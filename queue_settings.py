from django.conf import settings

if settings.DEBUG:
    max_queue_size = 12e6  # 12'000'000kb -> 12gb
    max_batch_size = 5e6  # 5'000'000kb -> 5gb
else:
    max_queue_size = 4.5e6  # 4'500'000kb -> 4.5gb
    max_batch_size = 9.8e5  # 980'000kb -> 980mb
