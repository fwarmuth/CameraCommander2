#ifndef PROTOCOL_H
#define PROTOCOL_H

#define FW_VERSION "1.0.1"

// Command tokens
#define CMD_VERSION 'V'
#define CMD_MOVE    'M'
#define CMD_STATUS  'S'
#define CMD_ENABLE  'E'
#define CMD_DISABLE 'D'
#define CMD_STOP    'X'

// Reply prefixes
#define REPLY_VERSION "VERSION "
#define REPLY_STATUS  "STATUS "
#define REPLY_DONE    "DONE"
#define REPLY_OK      "OK "
#define REPLY_ERR     "ERR "

#endif
