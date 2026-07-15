### WorkforceOS

Manufacturing workforce operating system that automatically allocates employees to production lines and machines.

#### Architecture

```
workforceos/
├── api/              # HTTP / whitelisted API entry points
├── services/         # Application use-case services
│   ├── attendance_service.py
│   ├── planning_service.py
│   ├── allocation_service.py
│   ├── assignment_service.py
│   ├── display_service.py
│   ├── rule_engine.py
│   ├── scoring_engine.py
│   └── validation_service.py
├── utils/            # Shared constants, exceptions, helpers
├── jobs/             # Scheduled background jobs
├── public/           # Static assets
└── templates/        # Jinja templates
```

#### License

MIT
