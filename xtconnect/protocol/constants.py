"""
PCMI protocol command codes and constants.

Based on VLink Node V2.9 CommConstantsU.pas and the .NET XTConnect.Controllers library.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Final


class CommandCode(IntEnum):
    """
    PCMI protocol command codes for PC-to-Controller communication.

    Command codes are single bytes that identify the type of message being sent
    or received. They are grouped by function:
    - 0x81-0x88: Connection management
    - 0x8F-0xBF: Data request/response
    - 0xA1-0xA9: Data upload
    - 0x99, 0x9B, 0xA3: Flow control
    - 0xC1-0xDB: Error responses
    """

    # ===== Connection Management =====

    PCMI_ATTENTION = 0x81
    """Attention command (not commonly used)."""

    PCMI_AT_ACK = 0x82
    """Attention acknowledgment."""

    PCMI_SERIAL_NUMBER = 0x85
    """Select controller by serial number."""

    PCMI_SN_ACK = 0x86
    """Serial number acknowledged - controller selected."""

    PCMI_BREAK = 0x87
    """Disconnect from controller."""

    PCMI_BR_ACK = 0x88
    """Disconnect acknowledged."""

    # ===== Data Request Commands (Downloads from Controller) =====

    PCMI_SEND_PARMDATA = 0x8F
    """Request device parameters for all devices."""

    PCMI_PD_STRING_1 = 0x90
    """Device parameters response (1-byte RLI)."""

    PCMI_PD_STRING_2 = 0xB7
    """Device parameters response (2-byte RLI)."""

    PCMI_SEND_VARDATA = 0x91
    """Request variable device data (runtime values)."""

    PCMI_VD_STRING_1 = 0x92
    """Variable device data response (1-byte RLI)."""

    PCMI_VD_STRING_2 = 0xB9
    """Variable device data response (2-byte RLI)."""

    PCMI_SEND_HISTORY = 0x93
    """Request history records."""

    PCMI_HA_STRING = 0x94
    """History record response."""

    PCMI_HA_NONSWAP_STRING = 0xB5
    """History record response (native byte order, no swap)."""

    PCMI_SEND_ZONE_PARM = 0x95
    """Request zone parameters."""

    PCMI_ZP_STRING_1 = 0x96
    """Zone parameters response (1-byte RLI)."""

    PCMI_ZP_STRING_2 = 0xB8
    """Zone parameters response (2-byte RLI)."""

    PCMI_SEND_ZONE_VAR = 0x97
    """Request zone variable data (runtime values)."""

    PCMI_ZV_STRING_1 = 0x98
    """Zone variable data response (1-byte RLI)."""

    PCMI_ZV_STRING_2 = 0xBA
    """Zone variable data response (2-byte RLI)."""

    PCMI_SEND_VERSION = 0x9F
    """Request version and system information."""

    PCMI_SV_STRING = 0xA0
    """Version record response."""

    PCMI_SEND_ALARM = 0xA4
    """Request alarm list."""

    PCMI_SA_STRING = 0xA5
    """Alarm list response."""

    PCMI_SA_NONSWAP_STRING = 0xB3
    """Alarm list response (native byte order, no swap)."""

    PCMI_SEND_PASSWORD = 0xA6
    """Request password records."""

    PCMI_PW_STRING = 0xA7
    """Password record response."""

    PCMI_SEND_DETAIL_ALARM = 0xAA
    """Request detailed alarm information."""

    PCMI_DA_STRING = 0xAB
    """Detailed alarm response."""

    PCMI_DA_NONSWAP_STRING = 0xB4
    """Detailed alarm response (native byte order, no swap)."""

    PCMI_GET_INFO_RECORD = 0xAC
    """Request GetInfo record."""

    PCMI_SEND_INFO_RECORD = 0xAD
    """GetInfo response (1-byte length)."""

    PCMI_SEND_INFO1_RECORD = 0xB2
    """GetInfo response (2-byte length)."""

    PCMI_SEND_INFO1_NONSWAP_RECORD = 0xB6
    """GetInfo response (2-byte length, native byte order)."""

    PCMI_SEND_SCALE_GLOBAL = 0xAE
    """Request scale global data."""

    PCMI_SG_STRING = 0xAF
    """Scale global data response."""

    PCMI_SEND_BIRD_HOUSE = 0xB0
    """Request bird house data."""

    PCMI_BH_STRING = 0xB1
    """Bird house data response."""

    # ===== Data Upload Commands (Uploads to Controller) =====

    PCMI_PD_CC_STRING_1 = 0xA1
    """Upload device parameters (1-byte RLI)."""

    PCMI_ZP_CC_STRING_1 = 0xA2
    """Upload zone parameters (1-byte RLI)."""

    PCMI_PW_CC_PASSWORD = 0xA8
    """Upload password record."""

    PCMI_PW_CC_ACK = 0xA9
    """Password upload acknowledged."""

    # ===== Flow Control Commands =====

    PCMI_OK_SEND_NEXT = 0x99
    """Master ready for next record (during multi-record download)."""

    PCMI_OK_CC_NEXT = 0xA3
    """Upload next record accepted (during parameter upload)."""

    PCMI_END_OF_RECORD = 0x9B
    """No more records available (end of multi-record sequence)."""

    PCMI_ER_TRY_AGAIN = 0xCA
    """Retry last request."""

    # ===== Error Response Codes =====

    PCMI_ERROR = 0xC1
    """Generic error."""

    PCMI_ER_PASSWORD = 0xC2
    """Invalid password."""

    PCMI_ER_SERIAL_NUM = 0xC3
    """Invalid serial number."""

    PCMI_ER_STRING = 0xC4
    """String/data error."""

    PCMI_ER_NO_ZONE = 0xC8
    """Zone not found."""

    PCMI_ER_HANDS_OFF = 0xCB
    """Controller in use (local operation active)."""

    PCMI_ER_CC_AGAIN = 0xCC
    """Resend upload record."""

    PCMI_ER_CC_DEVICE = 0xCD
    """Device not found during parameter upload."""

    PCMI_ER_CC_ZONE = 0xCE
    """Zone not found during parameter upload."""

    PCMI_ER_SUM_CHECK = 0xD9
    """Checksum error detected by controller."""

    PCMI_ER_START_UP = 0xDA
    """Controller starting up (indexing history)."""

    PCMI_ER_COM_LENGTH = 0xDB
    """Length mismatch error."""


class ProtocolConstants:
    """
    PCMI protocol constants.

    Contains frame delimiters, timing values, buffer sizes, and special markers
    used throughout the protocol implementation.
    """

    # ===== Frame Delimiters =====

    STX: Final[int] = 0x20
    """Start of frame delimiter (Space character)."""

    ETX: Final[int] = 0x0D
    """End of frame delimiter (Carriage Return)."""

    # ===== Timing Constants (in seconds for Python) =====

    DEFAULT_RECEIVE_TIMEOUT: Final[float] = 5.0
    """Default response timeout in seconds."""

    RETRY_DELAY: Final[float] = 1.0
    """Delay between retries in seconds."""

    MAX_RETRIES: Final[int] = 6
    """Maximum number of retry attempts."""

    MODEM_TIMEOUT: Final[float] = 120.0
    """Modem carrier detect timeout in seconds."""

    MODEM_PAUSE: Final[float] = 5.0
    """Delay between modem redials in seconds."""

    MODEM_RETRIES: Final[int] = 3
    """Modem retry count."""

    # ===== Buffer Sizes =====

    COM_BUFFER_SIZE: Final[int] = 2048
    """Maximum protocol message size in bytes."""

    SERIAL_NUMBER_LENGTH: Final[int] = 8
    """Maximum serial number length in characters."""

    # ===== Protocol Limits =====

    MAX_ZONES: Final[int] = 9
    """Maximum number of zones per controller."""

    MAX_GETINFO_SEQUENCE_RECORD: Final[int] = 5
    """Maximum GetInfo sequence record number per zone (0-5)."""

    HISTORY_HIGHEST_GROUP_NUMBER: Final[int] = 9
    """Highest history group number."""

    # ===== Special Values =====

    NAN_TEMP: Final[int] = 0x7FFF
    """Not-a-Number temperature marker (32767)."""

    BASE_YEAR_FOR_DATES: Final[int] = 1980
    """Base year for date calculations."""

    # ===== Serial Port Configuration =====

    DEFAULT_BAUD_RATE: Final[int] = 19200
    """Default baud rate for serial communication."""

    DEFAULT_DATA_BITS: Final[int] = 8
    """Default data bits."""

    DEFAULT_STOP_BITS: Final[int] = 1
    """Default stop bits."""


# Sets of command codes grouped by behavior for frame parsing

ACKNOWLEDGMENT_CODES: Final[frozenset[int]] = frozenset({
    CommandCode.PCMI_SN_ACK,
    CommandCode.PCMI_BR_ACK,
    CommandCode.PCMI_AT_ACK,
    CommandCode.PCMI_OK_CC_NEXT,
    CommandCode.PCMI_PW_CC_ACK,
    CommandCode.PCMI_END_OF_RECORD,
    CommandCode.PCMI_ERROR,
    CommandCode.PCMI_ER_NO_ZONE,
    CommandCode.PCMI_ER_TRY_AGAIN,
    CommandCode.PCMI_ER_HANDS_OFF,
    CommandCode.PCMI_ER_SUM_CHECK,
    CommandCode.PCMI_ER_START_UP,
    CommandCode.PCMI_ER_COM_LENGTH,
})
"""Command codes that are single-byte acknowledgments (no payload)."""

ONE_BYTE_RLI_COMMANDS: Final[frozenset[int]] = frozenset({
    CommandCode.PCMI_PD_STRING_1,
    CommandCode.PCMI_VD_STRING_1,
    CommandCode.PCMI_ZP_STRING_1,
    CommandCode.PCMI_ZV_STRING_1,
})
"""Commands using 1-byte RLI (2 hex chars)."""

TWO_BYTE_RLI_COMMANDS: Final[frozenset[int]] = frozenset({
    CommandCode.PCMI_PD_STRING_2,
    CommandCode.PCMI_VD_STRING_2,
    CommandCode.PCMI_ZP_STRING_2,
    CommandCode.PCMI_ZV_STRING_2,
})
"""Commands using 2-byte RLI (4 hex chars). RLI is always little-endian."""

VLI_COMMANDS: Final[frozenset[int]] = frozenset({
    CommandCode.PCMI_HA_STRING,
    CommandCode.PCMI_HA_NONSWAP_STRING,
    CommandCode.PCMI_SA_STRING,
    CommandCode.PCMI_SA_NONSWAP_STRING,
    CommandCode.PCMI_DA_STRING,
    CommandCode.PCMI_DA_NONSWAP_STRING,
    CommandCode.PCMI_SEND_INFO_RECORD,
    CommandCode.PCMI_SEND_INFO1_RECORD,
    CommandCode.PCMI_SEND_INFO1_NONSWAP_RECORD,
})
"""Commands using VLI (Variable Length Indicator)."""

ERROR_CODES: Final[frozenset[int]] = frozenset({
    CommandCode.PCMI_ERROR,
    CommandCode.PCMI_ER_PASSWORD,
    CommandCode.PCMI_ER_SERIAL_NUM,
    CommandCode.PCMI_ER_STRING,
    CommandCode.PCMI_ER_NO_ZONE,
    CommandCode.PCMI_ER_TRY_AGAIN,
    CommandCode.PCMI_ER_HANDS_OFF,
    CommandCode.PCMI_ER_CC_AGAIN,
    CommandCode.PCMI_ER_CC_DEVICE,
    CommandCode.PCMI_ER_CC_ZONE,
    CommandCode.PCMI_ER_SUM_CHECK,
    CommandCode.PCMI_ER_START_UP,
    CommandCode.PCMI_ER_COM_LENGTH,
})
"""All error response codes."""

NONSWAP_RESPONSE_CODES: Final[frozenset[int]] = frozenset({
    CommandCode.PCMI_HA_NONSWAP_STRING,
    CommandCode.PCMI_SA_NONSWAP_STRING,
    CommandCode.PCMI_DA_NONSWAP_STRING,
    CommandCode.PCMI_SEND_INFO1_NONSWAP_RECORD,
})
"""Response codes that indicate native byte order (little-endian, no swap)."""
