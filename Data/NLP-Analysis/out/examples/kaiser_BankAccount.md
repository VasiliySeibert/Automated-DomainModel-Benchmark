# BankAccount (kaiser) — Short NLT, simple diagram

**NLT length:** 616 chars, 109 words, 10 sentences


## Natural language text (excerpt)

```
The following description of a bank is given. Create a suitable class diagram from the given informal description.
A bank manages any number of customers. The first name and last name of type String are stored for each customer. A bank consists of any number of branches. A customer has at least one and at most five accounts. Each account has an owner who is a customer of the bank. There are two basic types of accounts: Current accounts and savings accounts. Each account has an account number of type int and a current account balance of type double. Current accounts also have an overdraft limit of type double.
```


## Diagram summary

- 6 classes, 0 enums, 5 relationships

### Classes and their attributes

| Class | Abstract | Attributes (type) | L1 | L2 | L3 | L4 | absent |
|---|---|---|---|---|---|---|---|
| Bank | False | — | ✓ | ✓ | ✓ | ✓ | no |
| Branch | False | — | ✗ | ✓ | ✗ | ✓ | no |
| Customer | False | firstName (String), lastName (String) | ✓ | ✓ | ✓ | ✓ | no |
| Account | False | accountNumber (int), balance (double) | ✓ | ✓ | ✓ | ✓ | no |
| SavingsAccount | False | — | ✓ | ✓ | ✓ | ✓ | no |
| CheckingAccount | False | overdraftLimit (double) | ✓ | ✓ | ✓ | ✓ | no |

### Relationships

| Source | Type | Target | Card src | Card tgt | Label | src absent? | tgt absent? |
|---|---|---|---|---|---|---|---|
| Bank | aggregation | Branch | 1 | * | — | no | no |
| Bank | association | Customer | * | * | — | no | no |
| Customer | directed | Account | 1 | 1..5 | — | no | no |
| Account | inheritance | SavingsAccount | — | — | — | no | no |
| Account | inheritance | CheckingAccount | — | — | — | no | no |

## Lex-match — interesting cases


## Dependency-graph bindings (first 8)


### Class↔Attribute

| Class | Attribute | Sentence | Path | Hops |
|---|---|---|---|---|
| Bank | accountNumber | #21 | `bank manages number` | 2 |
| Branch | accountNumber | #44 | `branches of number` | 2 |
| Customer | firstName | #29 | `customer for stored name` | 3 |
| Customer | lastName | #29 | `customer for stored name` | 3 |
| Customer | accountNumber | #21 | `customers of number` | 2 |
| Account | accountNumber | #53 | `accounts` | 0 |
| Account | balance | #92 | `account balance` | 1 |
| Account | overdraftLimit | #110 | `accounts have limit` | 2 |

### Class↔Relationship (best path per relationship)

| Source | Type | Target | # sentences | Best path | Hops |
|---|---|---|---|---|---|
| Bank | aggregation | Branch | 1 | `bank consists of number of branches` | 5 |
| Bank | association | Customer | 2 | `bank of customer` | 2 |
| Customer | directed | Account | 2 | `customer has accounts` | 2 |
| Account | inheritance | SavingsAccount | 5 | `accounts` | 0 |
| Account | inheritance | CheckingAccount | 5 | `accounts` | 0 |