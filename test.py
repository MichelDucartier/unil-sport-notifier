import os
from dotenv import load_dotenv
from src.usn.api.status import CourseStatusRequester
from src.usn.api.notifier import USNotifier

# status = CourseStatusRequester()
# sesison_infos = status.request_url(url="https://sport.unil.ch/?pid=80&aid=58#content")
# 
# print(sesison_infos)

notifier = USNotifier(interval=0)
notifier.add_watch_url("https://sport.unil.ch/?pid=80&aid=58#content")
print(notifier.watched_urls)

notifier.loop()
