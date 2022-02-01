# GitHub Follower Bot (WIP)
## Work In Progress
This bot is a WIP. There are still many features I plan to add and code I need to improve (I'm still fairly new to Python). I am uploading early to show progress and ensure others understand I didn't just copy and paste code (specifically the bot code) from another source.

The bot technically works, but it is missing the following features that will be added.

* No auto-purge functionality for users you're following (e.g. unfollow them after a period of days).
* A better randomized waiting time system including "active hours".
* Unexpected behavior is possible.

## Description
This is a GitHub Follower Bot made inside of a Django application. Management of the bot is done inside of Django's default admin center. The bot itself runs in the background of the Django application.

The bot works as the following.

* Runs as a background task in the Django application.
* Management of bot is done in the Django application's web admin center.
* After installing, add users. 
* After adding starting users, add them to the target and seed users list (the target user is the user who will be following others and the seed user is used to start off the spread of the invite list based off of the user's followers list).
* New/least updated users are parsed first up to the max users setting value followed by a random range wait time.
* A task is ran in the background for parsed users to make sure they're being followed by target users.
* Each follow and unfollow is followed by a random range wait time.

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
```

While you could technically run the Django application's development server for this bot since only the settings are configured through there, Django recommends reading [this](https://docs.djangoproject.com/en/3.2/howto/deployment/) for production use.

## Settings
Inside of the web interface, a settings model should be visible. The following settings should be inserted.

* **max_scan_users** - The maximum users to parse at once before waiting for scan time.
* **wait_time_follow_min** - The minimum number of seconds to wait after following or unfollowing a user.
* **wait_time_follow_max** - The maximum number of seconds to wait after following or unfollowing a user.
* **wait_time_list_min** - The minimum number of seconds to wait after parsing a user's followers page.
* **wait_time_list_max** - The maximum number of seconds to wait after parsing a user's followers page.
* **scan_time_min** - The minimum number of seconds to wait after parsing a batch of users.
* **scan_time_max** - The maximum number of seconds to wait after parsing a batch of users.
* **follow** - Whether to follow users or not (should be "True" or "False").
* **verbose** - Whether to output additional information (should be "True" or "False").

## Credits
* [Christian Deacon](https://github.com/gamemann)