# GitHub Follower Bot (WIP)
## Work In Progress
This bot is a WIP. There are still many features I plan to add and code I need to improve (I'm still fairly new to Python). I am uploading early to show progress and ensure others understand I didn't just copy and paste code (specifically the bot code) from another source.

The bot technically works, but it is missing the following features that will be added.

* A better randomized waiting time system including "active hours".
* Unexpected behavior is possible.

## My Motives
A few months ago, I discovered a few GitHub users following over 100K users who were obviously using bots. At first I was shocked because I thought GitHub was against massive following users, but after reading more into it, it appears they don't mind. This had me thinking what if I started following random users as well. Some of these users had a single GitHub.io project that received a lot of attention and I'd assume it's from all the users they were following. I decided to try this. I wanted to see if it'd help me connect with other developers and it certainly did/has! Personally, I haven't used a bot to achieve this, I was actually going through lists of followers from other accounts and following random users. As you'd expect, this completely cluttered my home page, but it also allowed me to discover new projects which was neat in my opinion.

While this is technically 'spam', the good thing I've noticed is it certainly doesn't impact the user I'm followiing much other than adding a single line in their home page stating I'm following them (or them receiving an email stating this if they have that on). Though, I could see this becoming annoying if many people/bots started doing it (perhaps GitHub could add a user setting that has a maximum following count of a user who can follow them or receive notifications when the user follows).

I actually think it's neat this is allowed so far because it allows others to discover your projects. Since I have quite a few networking projects on this account, I've had some people reach out who I followed stating they found my projects neat because they aren't into that field.

I also wouldn't support empty profiles made just for the purpose of mass following.

## USE AT YOUR OWN RISK
Even though it appears GitHub doesn't mind users massive following others (which I again, support), this is still considered a spam tactic. Therefore, please use this tool at your own risk. I'm not even going to be using it myself because I do enjoy manually following users. I made this project to learn more about Python.

## Description
This is a GitHub Follower Bot made inside of a Django application. Management of the bot is done inside of Django's default admin center. The bot itself runs in the background of the Django application.

The bot works as the following.

* Runs as a background task in the Django application.
* Management of bot is done in the Django application's web admin center.
* After installing, you must add a super user via Django (e.g. `python3 manage.py createsuperuser`).
* Navigate to the admin web center and add your target user (the user who will be following others) and seeders (users that start out the follow spread).
* After adding the users, add them to the target and seed user list.
* New/least updated users are parsed first up to the max users setting value followed by a random range wait scan time.
* A task is ran in the background for parsed users to make sure they're being followed by target users.
* Another task is ran in the background to retrieve target user's followers and if the Remove Following setting is on, it will automatically unfollow these specific users for the target users.
* Another task is ran that checks all users a target user is following and unfollows the user after *x* days (0 = doesn't unfollow).
* Each follow and unfollow is followed by a random range wait time which may be configured.

## Requirements
The following Python models are required and I'd recommend Python version 3.8 or above since that's what I've tested with.

```
django
aiohttp
```

You can install them like the below.

```bash
# Python < 3
python -m pip install django
python -m pip install aiohttp

pip install django
pip install aiohttp

# Python >= 3
python3 -m pip install django
python3 -m pip install aiohttp

pip3 install django
pip3 install aiohttp
```

## Installation
Installation should be performed like a regular Django application. This application uses SQLite as the database. You can read more about Django [here](https://docs.djangoproject.com/en/4.0/intro/tutorial01/). I would recommend the following commands.

```bash
# Make sure Django and aiohttp are installed for this user.

# Clone repository.
git clone https://github.com/gamemann/GitHub-Follower-Bot.git

# Change directory to Django application.
cd GitHub-Follower-Bot/src/github_follower

# Migrate database.
python3 manage.py migrate

# Run the development server on any IP (0.0.0.0) as port 8000.
python3 manage.py runserver 0.0.0.0:8000

# NOTE - If you don't want to expose the application publicly, bind it to a local IP above (e.g. 10.50.0.4:8000 instead 0f 0.0.0.0:8000).

# Create super user for admin web interface.
python3 manage.py createsuperuser
```

The web interface should be located at `http://<host/ip>:<port>`. For example.

http://localhost:8000

While you could technically run the Django application's development server for this bot since only the settings are configured through there, Django recommends reading [this](https://docs.djangoproject.com/en/3.2/howto/deployment/) for production use.

## Settings
Inside of the web interface, a settings model should be visible. The following settings should be inserted.

* **enabled** - Whether to enable the bot or not (should be "1" or "0").
* **max_scan_users** - The maximum users to parse at once before waiting for scan time.
* **wait_time_follow_min** - The minimum number of seconds to wait after following or unfollowing a user.
* **wait_time_follow_max** - The maximum number of seconds to wait after following or unfollowing a user.
* **wait_time_list_min** - The minimum number of seconds to wait after parsing a user's followers page.
* **wait_time_list_max** - The maximum number of seconds to wait after parsing a user's followers page.
* **scan_time_min** - The minimum number of seconds to wait after parsing a batch of users.
* **scan_time_max** - The maximum number of seconds to wait after parsing a batch of users.
* **follow** - Whether to follow users or not (should be "1" or "0").
* **verbose** - Verbose level for stdout (see levels below).
1. \+ Notification when a target user follows another user.
1. \+ Notification when a target user unfollows a user due to being on the follower list or purge.
1. \+ Notification when users are automatically created from follow spread.
* **user_agent** - The User Agent used to connect to the GitHub API.
* **seed** - Whether to seed (add any existing user's followers to the user list).
* **seed_min_free** - If above 0 and seeding is enabled, seeding will only occur when the amount of new users (users who haven't been followed by any target users) is below this value.

## FAQ
**What did you choose Django to use as an interface?**
While settings could have been configured on the host itself, I wanted an interface that was easily accessible from anywhere. The best thing for this would be a webssite in my opinion. Most of my experience is with Django which is why I chose that project.

## Credits
* [Christian Deacon](https://github.com/gamemann)