import irc.bot
import irc.connection
import irc.client
import functools
import requests
import sys
import ssl
from collections import defaultdict
from itertools import count as counter
import controller
from enum import Enum

COMMAND_INTERVAL = 10.0
WARN_TIME = 5.0
EXECUTE_TIME = 3.0
REMINDER_PERIOD = 25.0

REMINDERS = [
    "Hint: Movement commands are single letters u (up), d (down), l (left), r (right), s (space/wait), z (undo).",
    "Hint: Movement commands can be chained arbritrarily, for example u5lld3r.",
    "Hint: Type !retry to retry the level, or !back to go back to the previous map.",
]


class Action(Enum):
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4
    ENTER = 5
    RESTART = 6
    BACK = 7

class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, username, token, channel):
        self.token = token
        self.channel = '#' + channel
        self.past_commands = {}
        self.voting_open = False
        self.reminder_index = 0

        server = 'irc.chat.twitch.tv'
        port = 6697

        ssl_ctx = ssl.create_default_context()
        wrapper = functools.partial(ssl_ctx.wrap_socket, server_hostname=server)
        connect_factory=irc.connection.Factory(wrapper=wrapper)

        super().__init__([(server, port, token)], username, username, connect_factory=connect_factory)

    def on_welcome(self, c, e):
        print("Joining channel")
        c.join(self.channel)

    def on_join(self, c, e):
        self.open_command_voting()
        self.reactor.scheduler.execute_every(REMINDER_PERIOD, self.remind_commands)

    def remind_commands(self):
        self.connection.privmsg(self.channel, REMINDERS[self.reminder_index])
        self.reminder_index = (self.reminder_index + 1) % len(REMINDERS)

    def on_pubmsg(self, c, e):
        print("Got message:", e)
        if self.voting_open and len(e.arguments):
            cmd = e.arguments[0].strip()
            if len(cmd) == 0:
                return

            actions = []
            if cmd.startswith('!retry') or cmd.startswith('!restart'):
                actions.append(Action.RESTART)
            elif cmd.startswith('!back') or cmd.startswith('!return'):
                actions.append(Action.BACK)
            else:
                prev_action = None
                found_digit = False
                digits = ''
                for c in cmd + ' ':
                    if c.isdigit():
                        found_digit = True
                        digits += c
                    elif found_digit == True:
                        if prev_action is not None:
                            for _ in range(max(min(int(digits), 20), 1)-1):
                                actions.append(prev_action)
                            prev_action = None
                        found_digit = False
                        digits = ''

                    if c == 'u':
                        prev_action = Action.UP
                        actions.append(prev_action)
                    elif c == 'd':
                        prev_action = Action.DOWN
                        actions.append(prev_action)
                    elif c == 'l':
                        prev_action = Action.LEFT
                        actions.append(prev_action)
                    elif c == 'r':
                        prev_action = Action.RIGHT
                        actions.append(prev_action)
                    elif c == 's':
                        prev_action = Action.ENTER
                        actions.append(prev_action)
                        
            if len(actions) == 0:
                return
            actions = actions[:20]
            print("Adding actions", actions)
            self.past_commands[e.source] = actions


    def open_command_voting(self):
        self.voting_open = True
        self.connection.privmsg(self.channel, f"Voting open for {COMMAND_INTERVAL} seconds!")

        self.reactor.scheduler.execute_after(COMMAND_INTERVAL-WARN_TIME, self.close_warning)

    def close_warning(self):
        self.connection.privmsg(self.channel, f"Voting will close in {WARN_TIME} seconds!")
        self.reactor.scheduler.execute_after(WARN_TIME, self.close_voting)

    def close_voting(self):
        self.voting_open = False

        movements = ''

        for i in counter():
            action_counts = defaultdict(int)

            popular_action = None
            popular_count = 0
            owners_by_action = defaultdict(list)

            for owner, actions in self.past_commands.items():
                action = None
                try:
                    action = actions[i]
                except IndexError:
                    pass
                count = action_counts[action] + 1
                action_counts[action] = count

                owners_by_action[action].append(owner)

                if count > popular_count:
                    popular_action = action
                    popular_count = count

            # Delete any votes that were in the minority so we are ready for the next action.
            for action, owners in owners_by_action.items():
                if action != popular_action:
                    for owner in owners:
                        del self.past_commands[owner]


            if popular_action is None:
                if i == 0:
                    self.connection.privmsg(self.channel, "No commands detected. Waiting for next vote.")
                break

            if popular_action == Action.BACK:
                self.connection.privmsg(self.channel, "Going back to previous map.") 
                controller.back_to_map()
                break

            if popular_action == Action.RESTART:
                self.connection.privmsg(self.channel, "Restarting level.") 
                controller.restart()
                break

            if popular_action == Action.UP:
                movements += 'u'
                controller.movement('u')
            elif popular_action == Action.DOWN:
                movements += 'd'
                controller.movement('d')
            elif popular_action == Action.LEFT:
                movements += 'l'
                controller.movement('l')
            elif popular_action == Action.RIGHT:
                movements += 'r'
                controller.movement('r')
            elif popular_action == Action.ENTER:
                movements += 's'
                controller.movement('s')

        if len(movements):
            movements = ' '.join(movements)
            self.connection.privmsg(self.channel, f"Executing movements: {movements}")
        
        self.past_commands = {}
        self.reactor.scheduler.execute_after(EXECUTE_TIME, self.open_command_voting)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: twitchbot <username> <token> <channel>")
        sys.exit(1)

    username  = sys.argv[1]
    token     = sys.argv[2]
    channel   = sys.argv[3]

    bot = TwitchBot(username, token, channel)
    bot.start()