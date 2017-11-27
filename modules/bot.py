from __future__ import print_function

from sopel import module
import twitter

import datetime
import traceback

ALLOWED_NICKS = [
    'brson', 'acrichto', 'frewsxcv', 'shep',
    'aidanhs', 'TimNN', 'carols10cents', 'simulacrum',
    'erickt', 'aturon',
]

QUEUE = None
MSG = 1
INCIDENT = 2

TWIT_consumer_key        = ""
TWIT_consumer_secret     = ""
TWIT_access_token_key    = ""
TWIT_access_token_secret = ""

twit_api = twitter.Api(consumer_key=TWIT_consumer_key,
                       consumer_secret=TWIT_consumer_secret,
                       access_token_key=TWIT_access_token_key,
                       access_token_secret=TWIT_access_token_secret)
print(twit_api.VerifyCredentials())

@module.event('NOTICE')
@module.commands(r'STATUS .*')
def recognise_nick(bot, trigger):
    global QUEUE
    print('Nickserv handle, queue:', QUEUE, 'trigger:', trigger)
    if trigger.sender != 'NickServ':
        return
    if QUEUE is None:
        print('Nothing in queue, bailing')
        return
    _, queuenick, queueop, queuearg = QUEUE
    QUEUE = None
    parts = trigger.split(' ')
    assert parts.pop(0) == 'STATUS'
    if len(parts) > 3:
        print('Nicksev sent way too much stuff to handle, bailing')
        return
    if len(parts) < 1:
        print('NickServ sent bad status, bailing')
        return
    nick = parts.pop(0)
    if nick != queuenick:
        print('Mismatched nicks in queue and requested, bailing', queuenick, nick)
        return
    if len(parts) == 2:
        parts.pop()
    #if len(parts) == 2 and parts.pop() != nick:
    #    # Dunno what this would actually mean
    #    print('Mismatched usernames from nickserv, bailing')
    #    return
    assert len(parts) == 1
    try:
        authlevel = int(parts[0])
    except:
        print('Failed to parse authlevel, bailing')
        return
    # https://stackoverflow.com/questions/1682920/determine-if-a-user-is-idented-on-irc
    # Verified 3 is authed on mozilla. 2 has not yet been seen.
    if authlevel != 3:
        print('Unknown authlevel, bailing')
        return
    assert queueop in [MSG, INCIDENT]
    if queueop == MSG:
        status = twit_api.PostUpdate(queuearg)
        print('Posted', queuearg)
        print('Status', status)
        bot.say('https://twitter.com/{user}/status/{id}'.format(
                    user=status.user.screen_name, id=status.id_str),
                '#rust-infra')
    elif queueop == INCIDENT:
        assert queuearg in ['start', 'stop']
        if queuearg == 'start':
            twit_api.UpdateImage('error-incident.png')
            bot.say('Incident started', '#rust-infra')
        elif queuearg == 'stop':
            twit_api.UpdateImage('error-bandage.png')
            bot.say('Incident stopped', '#rust-infra')

# Shouldn't need [ ] around the space, but it becomes optional if they're removed...
@module.nickname_commands(r'incident[ ](?P<op>.*)')
def incident(bot, trigger):
    global QUEUE
    try:
        if trigger.is_privmsg:
            return
        if trigger.sender not in ['#rust-infra']:
            return
        if trigger.nick not in ALLOWED_NICKS:
            return
        if QUEUE is not None and (datetime.datetime.now() - QUEUE[0]).total_seconds() < 15:
            bot.say('Something already in queue, please wait for 15s...')
            return
        op = trigger.group('op').strip()
        if op not in ['start', 'stop']:
            bot.say('Incident operation not start or stop')
            return
        print('Received op', repr(op), 'from', trigger.nick)
        QUEUE = (datetime.datetime.now(), trigger.nick, INCIDENT, op)
        bot.say('STATUS ' + trigger.nick, 'NickServ')
    except:
        traceback.print_exc()
        bot.say('Bot failure, please chastise aidanhs')

# Shouldn't need [ ] around the space, but it becomes optional if they're removed...
@module.nickname_commands(r'tweet[ ](?P<tweet>.*)')
def tweet(bot, trigger):
    global QUEUE
    try:
        if trigger.is_privmsg:
            return
        if trigger.sender not in ['#rust-infra']:
            return
        if trigger.nick not in ALLOWED_NICKS:
            return
        if QUEUE is not None and (datetime.datetime.now() - QUEUE[0]).total_seconds() < 15:
            bot.say('Something already in queue, please wait for 15s...')
            return
        msg = trigger.group('tweet').strip()
        if len(msg) < 5:
            bot.say('Tweet too short')
            return
        print('Received msg', repr(msg), 'from', trigger.nick)
        QUEUE = (datetime.datetime.now(), trigger.nick, MSG, msg)
        bot.say('STATUS ' + trigger.nick, 'NickServ')
    except:
        traceback.print_exc()
        bot.say('Bot failure, please chastise aidanhs')
