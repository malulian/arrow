### Arrow Aviation MX

arrow aviation MX

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd ~
bench get-app https://github.com/malulian/arrow --branch develop
bench install-app arrow
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/arrow
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
