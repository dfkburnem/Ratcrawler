# Ratcrawler

This project provides a GUI for finding summoning pairs in DeFi Kingdoms. It allows users to search, filter, and group heroes based on various criteria, and find optimal summoning pairs within provided wallet addresses. The tool optionally allows users to view heroes available for sale or hire in the tavern and search for matches for an individual hero.

## Installation

You can install the package directly from the releases.

### Source Code

1. To install the package, run:

```bash
pip install https://github.com/dfkburnem/Ratcrawler/releases/download/v1.0.0/ratcrawler-1.0.0.tar.gz
```
2. Run script using:

```bash
ratcrawler
```

### Executable

Download the executable from the releases page and run it directly:

1. Go to the [releases page](https://github.com/dfkburnem/Ratcrawler/releases).
2. Download the executable file (Ratcrawler.exe).
3. Run the executable.

## Usage

1. **Update Addresses**: Update the "Addresses.txt" file with the wallet addresses to search for summoning matches.
2. **Select Main Class**: Choose the main class(es) of heroes you want to search for.
3. **Select Sub Class**: Choose the sub class(es) of heroes you want to search for.
4. **Set Summons Range**: Specify the minimum and maximum number of summons remaining.
5. **Set Generation Range**: Specify the minimum and maximum generation of heroes.
6. **Set Rarity Range**: Specify the minimum and maximum rarity of heroes.
7. **Set Level Range**: Specify the minimum and maximum level of heroes.
8. **Match Filters**: Choose to match heroes based on generation, summons, main class, sub class, cooldown status, level, and/or rarity.
9. **Ability Filters**: Select the ability type (basic, advanced, elite) and set the number of ability matches required.
10. **Optional Filters**: Enter Hero ID for single hero searching, sale price limit to search heroes for sale and/or hire price limit to search for heroes for hire.
11. **Start the Search**: Click the "Search" button to start the search process and display the results.
12. **Review Summoning Pairs**: Evaluate the pairs found based on filter settings, sorted by total mutation matches. Select the "View on ADFK" hyperlink to view the match on the Adventures in DFK website.

## Important Notes

- **Reference Files**: Ensure that the `addresses.txt` is located in the same directory from which the script or executable is run. If the "shrek.mp4" file is also located in the same directory, it will play on the first search after initialization.
- **Executable vs Script**: While the executable provides an easier way to run the application, it is not as trustless as running the script directly from the source code. If security and transparency are priorities, consider using the script.

## Tip Address

If you find this tool useful and would like to provide a tip/gift for my efforts, you can send it to the following address:

**Tip Address:** 0xF3b3b68B554817185A01576E775dB4466E42F126

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
