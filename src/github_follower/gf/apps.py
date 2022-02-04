from django.apps import AppConfig

import back_bone as bb
import os

class GfConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gf'
    verbose_name = 'GitHub Follower'


    def ready(self):
        env = os.environ.get("FIRST_THREAD")

        # Check if first thread has started since we want to spin it up on the second thread in development.
        if env is not None:
            from .models import Setting

            # Set settings. defaults.
            Setting.create("enabled", "0", False)
            Setting.create("max_scan_users", "10", False)
            Setting.create("wait_time_follow_min", "10", False)
            Setting.create("wait_time_follow_max", "30", False)
            Setting.create("wait_time_list_min", "5", False)
            Setting.create("wait_time_list_max", "30", False)
            Setting.create("scan_time_min", "5", False)
            Setting.create("scan_time_max", "60", False)
            Setting.create("verbose", "1", False)
            Setting.create("user_agent", "GitHub-Follower", False)
            Setting.create("seed", "1", False)
            Setting.create("seed_min_free", "64", False)
            Setting.create("max_api_fails", "5", False)
            Setting.create("lockout_wait_min", "1", False)
            Setting.create("lockout_wait_max", "10", False)
            Setting.create("seed_max_pages", "5", False)

            bb.parser.start()
        else:
            os.environ["FIRST_THREAD"] = 'True'