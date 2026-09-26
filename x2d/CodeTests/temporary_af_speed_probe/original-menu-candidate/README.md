# Original Menu and “Play Features” Candidate

## Scope

This directory contains the original source QML, project-owned SVG icon and desktop/offline checks for a twelfth X2D menu entry named “耍起功能”. It also contains a direct-GUI structural experiment for a master switch and an AF-C child switch.

Generated compiled QML units, vendor libraries, preload binaries, device installation scripts and persistent startup configuration are intentionally absent.

## Verified result

In a temporary one-minute device session, the user confirmed:

- the default focus popover showed AF-S/MF;
- the twelfth entry opened a stock-style scrollable page;
- the master switch enabled the AF-C child switch;
- enabling AF-C changed the popover to AF-S/AF-C/MF;
- disabling AF-C restored AF-S/MF;
- the top-left return control worked;
- the watchdog returned to the stock GUI and the temporary package was removed.

## Limits

The current source is not a reviewed persistent installation package. Half-press return, sleep/wake, first-render cost, memory use, cold boot and continuous-focus performance remain incomplete.

The desktop checks use local Qt/PySide input and stock resources supplied by the user. Passing them does not prove on-device performance or compatibility with another firmware.

