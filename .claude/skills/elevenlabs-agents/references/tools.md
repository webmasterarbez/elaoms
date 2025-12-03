# Tools Reference

Detailed configuration for ElevenLabs agent tools.

## Client Tools

Execute on client-side (browser/mobile). Register in your application code.

### Configuration

```json
{
  "name": "navigate_to_page",
  "description": "Navigate to a specific page in the application",
  "wait_for_response": true,
  "parameters": {
    "type": "object",
    "properties": {
      "page_name": {
        "type": "string",
        "description": "The page to navigate to (home, products, checkout)"
      }
    },
    "required": ["page_name"]
  }
}
```

### JavaScript Implementation

```javascript
import { Conversation } from "@11labs/client";

const conversation = await Conversation.startSession({
  agentId: "your_agent_id",
  clientTools: {
    navigate_to_page: async ({ page_name }) => {
      window.location.href = `/${page_name}`;
      return { success: true, navigated_to: page_name };
    },
    get_customer_details: async ({ customer_id }) => {
      const customer = await fetchCustomer(customer_id);
      return customer; // Returned to agent context
    }
  }
});
```

### Response Handling

When `wait_for_response: true`:
- Agent waits for tool to complete
- Return value added to conversation context
- Can assign values to dynamic variables

## Server Tools (Webhooks)

Call external APIs. Configure in dashboard or via API.

### Configuration

```json
{
  "type": "webhook",
  "name": "get_weather",
  "description": "Get current weather for a location",
  "api_schema": {
    "url": "https://api.weather.com/v1/current",
    "method": "GET",
    "query_params": {
      "location": {
        "type": "string",
        "description": "City name or coordinates"
      },
      "units": {
        "type": "string",
        "description": "Temperature units (metric/imperial)",
        "default": "metric"
      }
    }
  }
}
```

### Authentication Methods

**API Key** (in headers):
```json
{
  "headers": {
    "X-API-Key": "{{secrets.WEATHER_API_KEY}}"
  }
}
```

**OAuth2 Client Credentials**:
Configure in Workspace Auth Connections:
- Client ID, Client Secret
- Token URL
- Optional scopes

**JWT Bearer**:
- JWT signing secret
- Token URL, Algorithm (default: HS256)
- Claims: issuer, audience, subject

**Basic Auth**:
- Username, Password

### Dynamic Parameters

Agent extracts parameters from conversation:

```json
{
  "url": "https://api.example.com/orders/{order_id}",
  "path_params": {
    "order_id": {
      "type": "string",
      "description": "The order ID to look up"
    }
  },
  "body": {
    "customer_email": {
      "type": "string",
      "description": "Customer's email address"
    }
  }
}
```

### Ambient Audio

Play audio during tool execution:
```json
{
  "ambient_sound": "office_typing",
  "ambient_sound_volume": 0.3
}
```

## MCP Tools

Connect Model Context Protocol servers.

### Adding MCP Server

1. Navigate to MCP server integrations dashboard
2. Click "Add Custom MCP Server"
3. Configure:
   - **Name**: Descriptive name (e.g., "Zapier MCP Server")
   - **Description**: What the server provides
   - **Server URL**: MCP server endpoint (treat as secret)
   - **Secret Token**: Optional Authorization header
   - **HTTP Headers**: Additional headers if needed

### Approval Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| Always Ask | Requests permission each time | New integrations, sensitive tools |
| Fine-Grained | Per-tool approval settings | Mixed read/write operations |
| No Approval | Automatic tool execution | Fully trusted servers only |

### Fine-Grained Configuration

```json
{
  "tools": {
    "read_document": { "auto_approve": true },
    "delete_document": { "requires_approval": true },
    "dangerous_tool": { "disabled": true }
  }
}
```

### Security Considerations

- Review server security practices
- Limit data sent to MCP servers
- Implement prompt injection guardrails
- Use approval modes appropriately
- Monitor tool invocations

## System Tools

Built-in platform tools.

### end_call

Terminate the conversation:
```json
{
  "type": "system",
  "name": "end_call",
  "description": "End the current call when the conversation is complete"
}
```

### transfer_to_number

Transfer to human operator:
```json
{
  "type": "system", 
  "name": "transfer_to_number",
  "description": "Transfer to human support when user requests or issue is complex",
  "config": {
    "transfer_rules": [
      {
        "type": "conference",
        "number_type": "phone",
        "phone_number": "+1234567890",
        "condition": "When user requests human support"
      },
      {
        "type": "sip_refer",
        "number_type": "sip_uri",
        "sip_uri": "sip:support@pbx.example.com",
        "condition": "Technical escalation required"
      }
    ]
  }
}
```

**Transfer Types**:
- **Conference**: Calls destination, adds to conference, removes AI
- **SIP REFER**: Direct SIP transfer (requires SIP trunk)

### send_message

Send SMS/text during call:
```json
{
  "type": "system",
  "name": "send_message",
  "description": "Send confirmation text to user"
}
```

## Tool Best Practices

### Naming
- Use clear, descriptive names
- Avoid abbreviations
- Use snake_case or camelCase consistently

### Descriptions
- Explain when tool should be used
- Include expected parameters
- Specify format requirements

### System Prompt Integration

```
When the user asks about order status:
1. First use get_order_status with the order ID
2. If order ID unknown, ask user to provide it
3. Present the status in a friendly manner

For complex issues requiring human assistance:
- Use transfer_to_number when user explicitly requests
- Transfer automatically if unable to resolve after 3 attempts
```

### Error Handling

Configure fallback behavior:
```json
{
  "error_handling": {
    "on_timeout": "apologize and retry",
    "on_failure": "inform user and offer alternative",
    "max_retries": 2
  }
}
```
