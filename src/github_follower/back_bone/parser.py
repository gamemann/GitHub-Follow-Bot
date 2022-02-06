import github_api as ga
import json
import asyncio

import threading
import datetime
from django.conf import settings
from django.utils.timezone import make_aware
from django.db.models import F

import random

from asgiref.sync import sync_to_async

class Parser(threading.Thread):
    def __init__(self):
        # Initialize thread.
        super().__init__()

        # Set daemon to true.
        self.daemon = True

        self.running = False
        self.locked = False

        self.api = None

        self.global_token = None
        self.global_username = None

        self.parse_users_task = None
        self.retrieve_followers_task = None
        self.purge_following_task = None

        self.retrieve_and_save_task = None

    def run(self):
        print("Parser is running...")

        self.running = True

        # Start the back-end parser.
        asyncio.run(self.work())

    @sync_to_async
    def get_users(self, gnames, need_parse = True):
        import gf.models as mdl

        res = mdl.User.objects.all().exclude(username__in = gnames).order_by('needs_to_seed', F('last_parsed').asc(nulls_first = True))

        if need_parse:
            res.filter(needs_parsing = True)

        return list(res)

    @sync_to_async
    def get_target_users(self):
        import gf.models as mdl

        return list(mdl.Target_User.objects.all().select_related('user'))

    @sync_to_async
    def get_setting(self, key):
        import gf.models as mdl

        val = mdl.Setting.get(key = key)

        return val

    @sync_to_async
    def get_filtered(self, otype, params = {}, related = [], sort = []):
        if len(params) < 1:
            return list(otype.objects.all().distinct())
        else:
            items = otype.objects.filter(**params)

            if len(related) > 0:
                items = items.select_related(related)

            if len(sort) > 0:
                items = items.order_by(sort)

            return list(items)


    async def do_fail(self):
        if self.api is None:
            return

        # Increase fail count.
        self.api.add_fail()

        try:
            max_fails = int(await self.get_setting("max_api_fails"))
        except Exception as e:
            print("[ERR] parser.do_fail() :: Failed to receive max fails.")
            print(e)

            return

        if max_fails < 1:
            return

        if int(await self.get_setting("verbose")) >= 3:
            print("[VVV] Adding fail (" + str(self.api.fails) + " > " + str(max_fails) + ").")
        
        #  If fail count exceeds max fails setting, set locked to True and stop everything.
        if self.api.fails >= max_fails:
            self.running = False
            self.locked = True

            if int(await self.get_setting("verbose")) >= 1:
                print("[V] Bot stopped due to fail count exceeding. Waiting specified time frame until starting again.")

            # Run lockout task in background.
            try:
                await self.run_locked_task()
            except Exception as e:
                print("[ERR] parser.do_fail() :: Failed to lock bot.")

        return

    async def retrieve_and_save_followers(self, user):
        import gf.models as mdl

        # Ignore targeted users.
        targeted = True

        try:
            tmp = await self.get_filtered(mdl.Target_User, {"user": user})
            tmp = tmp[0]
        except Exception:
            targeted = False

        if targeted and tmp is None:
            targeted = False

        if targeted:
            return

        # Make sure we don't have enough free users (users who aren't following anybody)..
        free_users = int(await self.get_setting("seed_min_free"))

        if free_users > 0:
            target_users = await self.get_target_users()

            # Loop for target GitHub usernames to exclude from parsing list.
            gnames = []

            for user in target_users:
                gnames.append(user.user.username)

            users = await self.get_users(gnames)
            user_cnt = 0

            for user in users:
                if len(await self.get_filtered(mdl.Following, {"user": user})) < 1:
                    user_cnt = user_cnt + 1

            # If we have enough free users, 
            if user_cnt > free_users:
                return

        page = user.cur_page

        # Create a loop and go through.
        while True:
            # Make new connection got GitHub API and set user agent.
            if self.api is None:
                self.api = ga.GH_API()

            # Authenticate globally.
            if self.global_username is not None and self.global_token is not None:
                self.api.authenticate(self.global_username, self.global_token)

            res = None

            # Try sending request to GitHub API.
            try:
                res = await self.api.send("GET", '/users/' + user.username + '/followers?page=' + str(page))
            except Exception as e:
                print("[ERR] Failed to retrieve user's following list for " + user.username + " (request failure).")
                print(e)

                await self.do_fail()

                break

            # Check status code.
            if res[1] != 200 and res[1] != 204:
                await self.do_fail()

                break

            # Decode JSON.
            try:
                data = json.loads(res[0])
            except json.JSONDecodeError as e:
                print("[ERR] Failed to retrieve user's following list for " + self.username + " (JSON decode failure).")
                print(e)

                break

            # Make sure we have data, if not, break the loop.
            if len(data) < 1 or page >= int(await self.get_setting("seed_max_pages")):
                # Save page and user.
                user.cur_page = page

                await sync_to_async(user.save)()

                break

            for nuser in data:
                if "id" not in nuser:
                    print("[ERR] ID field not found in JSON data.")

                    continue

                if "login" not in nuser:
                    print("[ERR] ID field not found in JSON data.")

                    continue

                # Check if user exists already.
                exists = True

                try:
                    new_user = await self.get_filtered(mdl.User, {"username": nuser["login"]})
                    new_user = new_user[0]
                except Exception as e:
                    exists = False

                if exists and new_user is None:
                    exists = False

                if not exists:
                    # Create new user by username.
                    await sync_to_async(mdl.User.objects.create)(username = nuser["login"], parent = user.id, auto_added = True)

                    if int(await self.get_setting("verbose")) >= 3:
                        print("[V] Adding user " + nuser["login"] + " (parent " + user.username + ")")

            # Increment page
            page = page + 1
            
            await asyncio.sleep(float(random.randint(int(await self.get_setting("wait_time_list_min")), int(await self.get_setting("wait_time_list_max")))))

    async def loop_and_follow_targets(self, user):
        import gf.models as mdl

        # First, we should make sure we're following the target users.
        target_users = await self.get_target_users()

        for tuser in target_users:
            # Check if user exists already.
            exists = True

            try:
                fuser = await self.get_filtered(mdl.Following, {"target_user": tuser, "user": user})
                fuser = fuser[0]
            except Exception:
                exists = False

            if exists and fuser is None:
                exists = False

            # Check if we exist in the following list.
            if exists:
                continue

            # Follow target user.
            await tuser.follow_user(user)

            await asyncio.sleep(float(random.randint(int(await self.get_setting("wait_time_follow_min")), int(await self.get_setting("wait_time_follow_max")))))

    async def parse_user(self, user):
        if bool(int(await self.get_setting("seed"))) and not self.locked:
            if self.retrieve_and_save_task is None or self.retrieve_and_save_task.done():
                self.retrieve_and_save_task = asyncio.create_task(self.retrieve_and_save_followers(user))
        else:
            if self.retrieve_and_save_task is not None and self.retrieve_and_save_task in asyncio.all_tasks():
                self.retrieve_and_save_task.cancel()
                self.retrieve_and_save_task = None

        follow_targets_task = asyncio.create_task(self.loop_and_follow_targets(user))

        await asyncio.gather(follow_targets_task)

    async def purge_following(self):
        import gf.models as mdl

        secs_in_day = 86400

        while True:
            # Retrieve target users.
            target_users = await self.get_target_users()

            # Loop through target users.
            for tuser in target_users:
                # Make sure cleanup days is above 0 (enabled).
                if tuser.cleanup_days < 1:
                    continue

                # Retrieve the target user's following list.
                users = None

                try:
                    users = await self.get_filtered(mdl.Following, {"target_user": tuser, "purged": False}, related = ('user'), sort = ('time_added'))
                except Exception:
                    users = None

                # Make sure we have users and loop.
                if users is not None:
                    for user in users:
                        now = datetime.datetime.now().timestamp()
                        expired = user.time_added.timestamp() + (tuser.cleanup_days * secs_in_day)

                        # Check if we're expired.
                        if now > expired:
                            if int(await self.get_setting("verbose")) >= 3:
                                print("[VVV] " + user.user.username + " has expired.")

                            # Unfollow used and mark them as purged.
                            await tuser.unfollow_user(user.user)

                            # Set purged to true.
                            user.purged = True

                            # Save user.
                            await sync_to_async(user.save)()

                            # Wait follow time.
                            await asyncio.sleep(float(random.randint(int(await self.get_setting("wait_time_follow_min")), int(await self.get_setting("wait_time_follow_max")))))

            await asyncio.sleep(float(random.randint(int(await self.get_setting("wait_time_list_min")), int(await self.get_setting("wait_time_list_max")))))
        
    async def retrieve_followers(self):
        import gf.models as mdl

        while True:
            await asyncio.sleep(1)

            tusers = await self.get_target_users()

            for user in tusers:
                # Use GitHub API.
                if self.api is None:
                    self.api = ga.GH_API()

                # Authenticate.
                self.api.authenticate(user.user.username, user.token)
                
                page = 1

                # We'll want to create a loop through of the target user's followers.
                while True:
                    res = None

                    # Make connection.
                    try:
                        res = await self.api.send("GET", '/user/followers?page=' + str(page))
                    except Exception as e:
                        print("[ERR] Failed to retrieve target user's followers list for " + user.user.username + " (request failure).")
                        print(e)

                        await self.do_fail()

                        break

                    # Check status code.
                    if res[1] != 200 and res[1] != 204:
                        await self.do_fail()

                        break

                    # Decode JSON.
                    try:
                        data = json.loads(res[0])
                    except json.JSONDecodeError as e:
                        print("[ERR] Failed to retrieve target user's followers list for " + user.user.username + " (JSON decode failure).")
                        print(e)

                        break

                    # Make sure we have data, if not, break the loop.
                    if len(data) < 1:
                        break

                    for fuser in data:
                        if "id" not in fuser:
                            continue

                        # Make sure user exists.
                        exists = True

                        muser = None

                        try:
                            muser = await self.get_filtered(mdl.User, {"username": fuser["login"]})
                            muser = muser[0]
                        except Exception:
                            exists = False

                        if exists and muser is None:
                            exists = False

                        if not exists:
                            muser = await sync_to_async(mdl.User.objects.create)(username = fuser["login"], needs_parsing = False)

                        # Add to follower list if not already on it.
                        exists = True

                        try:
                            tmp = await self.get_filtered(mdl.Follower, {"target_user": user, "user": muser})
                            tmp = tmp[0]
                        except Exception:
                            exists = False

                        if exists and tmp is None:
                            exists = False

                        await sync_to_async(user.save)()

                        # Make a new follower entry.
                        if not exists:
                            await sync_to_async(mdl.Follower.objects.create)(target_user = user, user = muser)

                        # Check if the same user is following our target.
                        exists = True

                        try:
                            tmp = await self.get_filtered(mdl.Following, {"target_user": user, "user": muser, "purged": False})
                            tmp = tmp[0]
                        except Exception:
                            exists = False

                        if exists and tmp is None:
                            exists = False
                        
                        # Check if target user is following this user.
                        if exists:
                            #  Check for remove following setting. If enabled, unfollow user.
                            if user.remove_following:
                                await user.unfollow_user(muser)

                                # We'll want to wait the follow period.
                                await asyncio.sleep(float(random.randint(int(await self.get_setting("wait_time_follow_min")), int(await self.get_setting("wait_time_follow_max")))))

                    # Increment page
                    page = page + 1

                    await asyncio.sleep(float(random.randint(int(await self.get_setting("wait_time_list_min")), int(await self.get_setting("wait_time_list_max")))))
        
    async def parse_users(self):
        import gf.models as mdl

        while True:
            # Retrieve users.
            target_users = await self.get_target_users()
            max_users = int(await self.get_setting("max_scan_users"))

            # Loop for target GitHub usernames to exclude from parsing list.
            gnames = []

            for user in target_users:
                gnames.append(user.user.username)

            # Retrieve users excluding target users.
            users = await self.get_users(gnames)

            for user in users[:max_users]:
                # Update last parsed.
                user.last_parsed = make_aware(datetime.datetime.now())

                # Check if this user needed to seed.
                if user.needs_to_seed:
                    user.needs_to_seed = False

                # Save user.
                await sync_to_async(user.save)()

                # Parse user.
                await self.parse_user(user)

            # Wait scan time.
            await asyncio.sleep(float(random.randint(int(await self.get_setting("scan_time_min")), int(await self.get_setting("scan_time_max")))))
            
    async def work(self):
        # Retrieve all target users
        tusers = await self.get_target_users()

        # Set global username and token.s
        for user in tusers:
            if user.global_user:
                self.global_username = user.user.username
                self.global_token = user.token

        # Create a loop until the program ends.
        while True:
            # Check if we're enabled.
            if bool(int(await self.get_setting("enabled"))) and not self.locked:
                # Run parse users task.
                if self.parse_users_task is None or self.parse_users_task.done():
                    self.parse_users_task = asyncio.create_task(self.parse_users())

                # Create tasks to check followers/following for target users.
                if self.retrieve_followers_task is None or self.retrieve_followers_task.done():
                    self.retrieve_followers_task = asyncio.create_task(self.retrieve_followers())
                
                if self.purge_following_task is None or self.purge_following_task.done():
                    self.purge_following_task = asyncio.create_task(self.purge_following())
            else:
                # Check tasks and make sure they're closed.
                if self.parse_users_task in asyncio.all_tasks():
                    self.parse_users_task.cancel()
                    self.parse_users_task = None

                if self.retrieve_and_save_task in asyncio.all_tasks():
                    self.retrieve_and_save_task.cancel()
                    self.retrieve_and_save_task = None
                
                if self.purge_following_task in asyncio.all_tasks():
                    self.purge_following_task.cancel()
                    self.purge_following_task = None

                if self.retrieve_followers_task is not None and self.retrieve_followers_task in asyncio.all_tasks():
                    self.retrieve_followers_task.cancel()
                    self.retrieve_followers_task = None

            # Sleep for a second to avoid CPU consumption.
            await asyncio.sleep(1)

    async def run_locked(self):
        wait_time = float(random.randint(int(await self.get_setting("lockout_wait_min")), int(await self.get_setting("lockout_wait_max"))) * 60)

        await asyncio.sleep(wait_time)

        self.locked = False
        self.running = True
        self.api.fails = 0

    async def run_locked_task(self):
        asyncio.create_task(self.run_locked())

parser = Parser()