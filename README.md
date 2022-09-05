# Brick Automator

Simple script for automating and customizing the (un)bricking

## Installation

Install the required packages

```
pip install -r requirements.txt
```

## How to use

### Basic usage

Run the following command where:
* The update_authority wallet should be the path to wallet private key in base58 format or
a json array format.
* The API_TOKEN can be obtained from the CoralCube team.

```
python main.py <PATH_TO_UPDATE_AUTHORITY_WALLET> <API_TOKEN>
```

For learning about more advanced usages run

```
python main.py --help
```
