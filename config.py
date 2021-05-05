"""
Bot Configuration File.
Made by Tpmonkey.
"""

### ---------- General ---------- ###

version = "1.0.15"
note = [
    "- Fixed RuntimeError while trying to delete passed assignment.",
    "- Fixed Bot spamming log messages and got rate-limited."
]

prefix = "," # Bot Prefix.
# --------------------------------- #

### ---------- Discord ---------- ###

# Bot Channels.
log_channel_id = 797471940411392061
dm_channel_id = 797471965891264592
image_channel_id = 810802238682824744
dump_channel_id = 833825510219972638
# --------------------------------- #

### -------- Extensions -------- ###

# Cooldown for loop
update_work_cooldown = 5 # mins
check_day_cooldown = 1 # min
kus_news_cooldown = 6 # hours

# KUS News URL
main_url = "http://www.kus.ku.ac.th/"
news_url = "http://www.kus.ku.ac.th/news.php"
# --------------------------------- #

### ----- System limitation ----- ###

assignment_limit = 24 # Assignment limit in one guild.
maximum_days = 30 # Maximum days of assignment to stay in the system, once passed it will be delete.
# --------------------------------- #