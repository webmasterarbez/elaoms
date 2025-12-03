---
name: Global Validation
description: "Implement comprehensive input validation on both client and server sides with clear error messages and security-first approaches. Use this skill when: (1) Validating user input from forms or API requests, (2) Implementing server-side validation (always required), (3) Adding client-side validation for better UX, (4) Sanitizing input to prevent injection attacks (SQL, XSS, command), (5) Validating data types, formats, and ranges, (6) Creating field-specific error messages, (7) Implementing business rule validation, (8) Using allowlists instead of blocklists for security, (9) Validating API request payloads with Pydantic, Zod, or similar, (10) Ensuring consistent validation across all entry points."
---

# Global Validation

## When to use this skill:

- When validating user input from forms or API requests
- When implementing server-side validation (always required, never trust client)
- When adding client-side validation for better UX (but duplicate on server)
- When sanitizing input to prevent injection attacks (SQL, XSS, command injection)
- When validating data types, formats, and ranges
- When creating field-specific error messages that help users correct input
- When implementing business rule validation (e.g., sufficient balance, valid dates)
- When using allowlists instead of blocklists for security
- When validating API request payloads with Pydantic, Zod, Joi, or similar
- When ensuring consistent validation across all entry points (web forms, APIs, jobs)
- When failing early with clear validation errors before processing

## Instructions

For details, refer to the information provided in this file:
[global validation](../../../agent-os/standards/global/validation.md)