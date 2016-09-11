import re

from errbot import BotPlugin
import sleekxmpp


class BridgeBot(sleekxmpp.ClientXMPP):
    def __init__(self, slack, log, config):
        super(BridgeBot, self).__init__(config.XMPP_BRIDGE_JID, config.XMPP_BRIDGE_PASSWORD)

        self.slack = slack
        self.log = log
        self.nick = config.XMPP_BRIDGE_NICK
        self.channel_map = config.XMPP_BRIDGE_CHANNEL_MAP
        self.channel_host = config.XMPP_BRIDGE_HOST
        self.add_event_handler('session_start', self.start)
        self.add_event_handler('groupchat_message', self.muc_message)
        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0045') # Multi-User Chat
        self.register_plugin('xep_0199') # XMPP Ping
        if self.connect():
            self.process()

    def start(self, event):
        self.get_roster()
        self.send_presence()

    def muc_message(self, msg):
        self.log.info(msg)
        if msg['mucnick'] != self.nick and self.nick in msg['body']:
            slack_body = re.sub('{}[,:]\s+'.format(self.nick), '', msg['body'])
            self.slack.send(
                self.slack.build_identifier(self.slackchannel(msg['from'].user)),
                '{}: {}'.format(msg['mucnick'], slack_body)
            )

    def mappedMUC(self, slackchannel):
        if slackchannel in self.channel_map:
            slackchannel = self.channel_map[slackchannel]

        return '{}@{}'.format(slackchannel, self.channel_host)

    def slackchannel(self, room_name):
        inv_map = {v: k for k, v in self.channel_map.items()}
        if room_name in inv_map:
            room_name = inv_map[room_name]

        return '#{}'.format(room_name)

    def room(self, slackchannel):
        room = self.mappedMUC(slackchannel)
        if room not in self.plugin['xep_0045'].getJoinedRooms():
            self.plugin['xep_0045'].joinMUC(room, self.nick, wait=True)

        return room

    def send_msg(self, message, channel):
        self.send_message(self.room(channel), message, mtype='groupchat')

class Xmppbridge(BotPlugin):
    '''
    Bridge channels to XMPP MUCs
    '''

    def activate(self):
        '''
        Triggers on plugin activation

        You should delete it if you're not using it to override any default behaviour
        '''
        super(Xmppbridge, self).activate()

    def deactivate(self):
        '''
        Triggers on plugin deactivation

        You should delete it if you're not using it to override any default behaviour
        '''
        super(Xmppbridge, self).deactivate()
        self.bridgebot.disconnect(wait=True)

    def get_configuration_template(self):
        '''
        Defines the configuration structure this plugin supports

        You should delete it if your plugin doesn't use any configuration like this
        '''
        return {'XMPP_BRIDGE_JID': 'user@example.com',
                'XMPP_BRIDGE_PASSWORD': 'password',
                'XMPP_BRIDGE_NICK': 'bridgebot',
                'XMPP_BRIDGE_HOST': 'conferenc.example.com'
               }

    def check_configuration(self, configuration):
        '''
        Triggers when the configuration is checked, shortly before activation

        Raise a errbot.utils.ValidationException in case of an error

        You should delete it if you're not using it to override any default behaviour
        '''
        super(Xmppbridge, self).check_configuration(configuration)

    def callback_connect(self):
        '''
        Triggers when bot is connected
        '''
        self.bridgebot = BridgeBot(
            self,
            self.log,
            self._bot.bot_config
        )

    def callback_message(self, message):
        '''
        Triggered for every received message that isn't coming from the bot itself
        '''
        if not self.bot_identifier.nick == message.frm.nick:
            bridge_message = '{}: {}'.format(message.frm.nick, message.body)
            self.bridgebot.send_msg(bridge_message, message.frm.room.name)
