from django.db import models
import json
import http.client

import back_bone

import asyncio

import github_api as ga

from asgiref.sync import sync_to_async

class Setting(models.Model):
    key = models.CharField(verbose_name = "Key", help_text="The setting key.", max_length = 64)
    val = models.CharField(verbose_name = "Value", help_text="The setting value.", max_length = 64)

    def create(key, val, override):
        item = None

        exists = True

        try:
            item = Setting.objects.filter(key = key)[0]
        except Exception:
            exists = False

        if item is None:
            exists = False

        if exists:
            # Make sure we want to override.
            if not override:
                return 
        else:
            item = Setting(key = key)

        # Set value and save.
        item.val = val
        item.save()

    def get(key):
        val = None
        exists = True

        try:
            item = Setting.objects.filter(key = key)[0]
        except Exception:
            exists = False

        if exists and item is None:
            exists = False

        if exists:
            val  = str(item.val)

        return val

    def __str__(self):
        return self.key

class User(models.Model):
    gid = models.IntegerField(editable = False, null = True)
    parent = models.IntegerField(editable = False, default = 0, null = True)

    username = models.CharField(verbose_name = "Username", help_text = "The GitHub username.", max_length = 64, unique = True)

    last_updated = models.DateTimeField(editable = False, auto_now_add = True, null = True)
    last_parsed = models.DateTimeField(editable = False, auto_now_add = True, null = True)
    seeded = models.BooleanField(editable = False, default = False)
    auto_added = models.BooleanField(editable = False, default = False)

    async def retrieve_github_id(self):
        api = ga.GH_API()

        if back_bone.parser.global_token is None or back_bone.parser.global_username is None:
            return

        api.authenticate(back_bone.parser.global_username, back_bone.parser.global_token)

        # Send request.
        try:
            await api.send('GET', '/users/' + self.username)
        except Exception as e:
            print("[ERR] Failed to retrieve Github ID for user " + self.username + " (request failure).")
            print(e)

            return

        # Read response.
        try:
            resp = await api.retrieve_response()
        except Exception as e:
            print("[ERR] Failed to retrieve GitHub ID for user " + self.username + " (response failure).")
            print(e)

            return

        # Close connection.
        try:
            await api.close()
        except Exception as e:
            print("[ERR] HTTP close error.")
            print(e)

        # Decode JSON.
        try:
            data = json.loads(resp)
        except json.JSONDecodeError as e:
            print("[ERR] Failed to retrieve GitHub ID for user " + self.username + " (JSON decode failure).")
            print(e)

            return

        # Store GitHub ID.
        if "id" in data:
            self.gid = int(data["id"])
        else:
            print("[ERR] Failed to retrieve GitHub ID for user " + self.username + " (ID doesn't exist in JSON data).")
            return 

    def save(self, *args, **kwargs):
        try:
            super().save(*args, **kwargs)
        except Exception as e:
            print("[ERR] Error saving user.")
            print(e)

            return

        asyncio.run(self.retrieve_github_id())

    def __str__(self):
        return self.username

class Target_User(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    remove_following = models.BooleanField(verbose_name = "Remove Following", help_text = "Whether to remove a user that follows from the following list.", default = True)
    cleanup_days = models.IntegerField(verbose_name = "Cleanup Days", help_text = "Automatically purges uses from the following list after this many days.")
    token = models.CharField(verbose_name = "Personal Token", help_text = "GitHub's personal token for authentication.", max_length=128)
    global_user = models.BooleanField(verbose_name = "Global User", help_text = "If true, this user's token and username will be used for authentication in general.", default=False)

    async def follow_user(self, user):
        # Check if we should follow.
        if not bool(await sync_to_async(Setting.get)(key = "follow")):
            return

        # Make connection GitHub's API.
        api = ga.GH_API()

        # Authenticate
        api.authenticate(self.user.username, self.token)

        # Send request.
        try:
            await api.send('PUT', '/user/following/' + user.username)
        except Exception as e:
            print("[ERR] Failed to follow GitHub user " + user.username + " for " + self.user.username + " (request failure).")
            print(e)

            return

        # Close connection.
        try:
            await api.close()
        except Exception as e:
            print("[ERR] HTTP close error.")
            print(e)

        # Save to following.
        new_following = Following(target_user = self, user = user)

        await sync_to_async(new_following.save)()

        if bool(await sync_to_async(Setting.get)(key = "verbose")):
            print("[V] Following user " + user.username + " for " + self.user.username + ".")

    async def unfollow_user(self, user):
        # Make connection GitHub's API.
        api = ga.GH_API()

        # Authenticate
        api.authenticate(self.user.username, self.token)

        # Send request.
        try:
            await api.send('DELETE', '/user/following/' + user.username)
        except Exception as e:
            print("[ERR] Failed to unfollow GitHub user " + user.username + " for " + self.user.username + " (request failure).")
            print(e)

            return

        # Close connection.
        try:
            await api.close()
        except Exception as e:
            print("[ERR] HTTP close error.")
            print(e)

        # Deleting from following list.
        exists = True

        following = None

        try:
            following = await sync_to_async(Following.objects.get)(target_user = self, user = user)
        except Exception:
            exists = False

        if following is None:
            exists = False

        if exists:
            following.delete()

        if bool(await sync_to_async(Setting.get)(key = "verbose")):
            print("[V] Unfollowing user " + user.username + " from " + self.user.username + ".")

    def __str__(self):
        return self.user.username

class Follower(models.Model):
    target_user = models.ForeignKey(Target_User, on_delete = models.CASCADE)
    user = models.ForeignKey(User, on_delete = models.CASCADE)

    time_added = models.DateTimeField(editable = False, auto_now_add = True)

    def __str__(self):
        return self.user.username

class Following(models.Model):
    target_user = models.ForeignKey(Target_User, on_delete = models.CASCADE)
    user = models.ForeignKey(User, on_delete = models.CASCADE)
    purged = models.BooleanField(editable = False, default = False)

    time_added = models.DateTimeField(editable = False, auto_now_add = True)

    def __str__(self):
        return self.user.username

class Seeder(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE)

    def __str__(self):
        return self.user.username