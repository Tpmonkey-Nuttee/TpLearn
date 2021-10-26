"""
Bot Configuration File.
Made by Tpmonkey
"""

### ---------- General ---------- ###

version = "1.5"
note = [
    "**New Command!**",
    "- Recommendation command (aliase is `rec`)",
    "Recommend next song based on __current song__ or __name/spotify track url__ that was given.",
    "This command uses Spotify Recommendation System and Will queue 20 more tracks for you!",
    "*Dev Note:*",
    "*- Before using command, __You need to use play command first__.*"
    "*- Normally, Youtube title is bad. So try to search it yourself is a better option.*",
    "",
    "**QoL**",
    "- Bot auto-disconnect and timeout system have been improved.",
    "",
    "**Bugs**",
    "- Fixed Loop & Loop queue commands sometimes don't work at all(?)"
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
update_work_cooldown = 2 # mins
check_day_cooldown = 1 # min
kus_news_cooldown = 4 # hours

# KUS News URL
main_url = "http://www.kus.ku.ac.th/"
news_url = "http://www.kus.ku.ac.th/news.php?type=0"
# --------------------------------- #

### ----- System limitation ----- ###

assignment_limit = 24 # Assignment limit in one guild.
maximum_days = 30 # Maximum days of assignment to stay in the system, once passed it will be delete.
MAX_REMINDER_PER_DAY = 5 # Idk why those 2 are lower case. but this is the maximum reminder per day.
# --------------------------------- #

### -- Random Facts and Quotes -- ###
facts = [
    f"You can use `{prefix}setup` to setup the bot!",
    f"To view all the assignments, simple type `{prefix}allworks`"
    "This bot was created by Nuttee, as a KUS senior project.",
    "Source code of the bot can be found in Github [here](https://github.com/Tpmonkey-Nuttee/TpLearn-BETA) !",
    "Colour of most embed will be base on assignment date.",
    "Sometimes, Bot needs to rest like you!", "This bot was created entirely in python.",
    f"Have a problem with bot channels not working properly? Use `{prefix}fix` command!",
    "To use add command, You need to wait for the bot to finish adding reactions and type the message you want to add!",
    "You cannot use some commands in bot DM!", "Most of the commands have cooldown timer, So don't spam it!",
    "Old Assignments will be remove automatically when It passed certain days to reduce data usage!",
    "Did you know that, You can hold the assignment embed to copy the key in mobile? What a nice touch!",
    f"Right now, The Bot version is `{version}`", "This project was created as a fun joke, But somehow ended up like this!",
    f"You can monitor KUS website using `{prefix}set-news` command!", "A lot of commands have aliases, so they can be type quicker!",
    "When you clicked on reaction in edit/add menu, The Bot will not remove it but It knows that you clicked!",
    "You don't need to click reactions in edit/add menu to cycle the title, It is automatically!",
    "There are a secret commands, Try to find them all! (But don't forget about assignments ;) )",
    "The Add, Edit, Help menu has a timeout!", "~~Today is Sunday!~~", "What if I tell you that the bot can think like human?",
    "This is a fact!?", f"You can see facts throught `{prefix}fact` command!", "Don't forget to drink some water!",
    "Have you take a break yet?", "Don't forget to sleep!", "Did you sort your backpack yet?", "What is today homework?",
    "Don't forget to go outside! but Not on the Pandemic...", "[?](https://www.youtube.com/watch?v=dQw4w9WgXcQ)", ":eyes:",
    '"The way to get started is to quit talking and begin doing." -Walt Disney', 
    '"Always remember that you are absolutely unique. Just like everyone else." -Margaret Mead',
    '"The future belongs to those who believe in the beauty of their dreams." -Eleanor Roosevelt',
    '"Tell me and I forget. Teach me and I remember. Involve me and I learn." -Benjamin Franklin',
    '"The best and most beautiful things in the world cannot be seen or even touched - they must be felt with the heart." -Helen Keller',
    '"It is during our darkest moments that we must focus to see the light." -Aristotle',
    '"You will face many defeats in life, but never let yourself be defeated." -Maya Angelou',
    '"Life is either a daring adventure or nothing at all." -Helen Keller',
    '"Many of life\'s failures are people who did not realize how close they were to success when they gave up." -Thomas A. Edison',
    '"You have brains in your head. You have feet in your shoes. You can steer yourself any direction you choose." -Dr. Seuss',
    '"If you really look closely, most overnight successes took a long time." -Steve Jobs',
    '"If you can\'t explain it simply, you don\'t understand it well enough." -Albert Einstein',
    '"No problem can be solved from the same level of consciousness that created it." -Albert Einstein',
    '"Insanity: doing the same thing over and over again and expecting different results." -Albert Einstein', 
    '"Two things are infinite: the universe and human stupidity; and I\'m not sure about the universe." -Albert Einstein',
    "Facts: Facts has 50 random texts.", "This project contained over 3,000+ lines of code, wrote single handedly by one person. Very bad!", "The facts command was added on 9th May 2021, How long was it now?", "Who ever developed me is a madman."
    "You know, I can sing a song for you right?", "I have a beautiful voice.", "No."
]
# --------------------------------- #