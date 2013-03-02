simato
======

Simple Magnetic Card Reader/Writer Tool for Omron 3S4YR-MVFW1JD

This is simple python code to control a Omron 3S4YR-MVFW1JD card reader via a serial port.

Features:
- Reading of Track 1-3
- Writing of Track 1-3
- Simple Track memory function to be able to copy track content
- Raw commands to the CardReaderWriter

[datasheet]: https://www.relayspec.com/specs/021320/D23MVFMVS0600.pdf
[transmission]: http://libmsr.googlecode.com/files/omron-data-transmission.pdf


The Card Readers/Writers datasheet can be found [here][datasheet].
To dig deeper into the protocol, have a look [here][transmission].

Although the device has also the capability to access the smart card, i didn't spend any time on this stuff yet. 





