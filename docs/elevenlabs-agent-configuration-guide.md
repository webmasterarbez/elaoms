# ElevenLabs Agent Configuration Guide

A comprehensive guide to creating conversational voice AI agents using the ElevenLabs Agents Platform API, with full integration support for the OpenMemory system.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [API Reference](#api-reference)
- [Configuration Schema](#configuration-schema)
- [Agent Examples](#agent-examples)
  1. [Customer Support Agent](#1-customer-support-agent)
  2. [Sales & Lead Qualification Agent](#2-sales--lead-qualification-agent)
  3. [Healthcare Appointment Agent](#3-healthcare-appointment-agent)
  4. [E-commerce Agent](#4-e-commerce-agent)
  5. [IT Helpdesk Agent](#5-it-helpdesk-agent)
  6. [Financial Services Agent](#6-financial-services-agent)
  7. [Hospitality Agent](#7-hospitality-agent)
  8. [Memoir Writer Interviewer Agent](#8-memoir-writer-interviewer-agent)
- [OpenMemory Integration](#openmemory-integration)
- [Webhook Configuration](#webhook-configuration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

The ElevenLabs Agents Platform provides a powerful API for creating conversational voice AI agents. This guide covers:

- **Agent Creation**: How to configure and deploy agents via the API
- **Voice Configuration**: TTS settings for natural speech synthesis
- **Tool Integration**: Webhooks, client tools, and MCP connections
- **Conversation Flow**: Turn-taking, timeouts, and interruption handling
- **Data Collection**: Extracting structured information from conversations
- **OpenMemory Integration**: Persistent memory for personalized experiences

### Architecture Flow

```
User Call → Telephony (Twilio/SIP) → ElevenLabs Agent
                                          ↓
                    ┌─────────────────────┼─────────────────────┐
                    ↓                     ↓                     ↓
            ASR (Speech-to-Text)    LLM (GPT/Claude)    TTS (Voice Synthesis)
                    ↓                     ↓                     ↓
            User Transcript     Agent Response Text     Agent Audio Output
                                          ↓
                              Webhooks → OpenMemory
```

---

## Prerequisites

### Required Credentials

1. **ElevenLabs API Key**: Get from [ElevenLabs Settings](https://elevenlabs.io/app/settings/api-keys)
2. **Voice ID**: Choose from [ElevenLabs Voice Library](https://elevenlabs.io/app/voice-library)
3. **OpenMemory Key** (optional): For persistent caller memory

### Environment Setup

Create a `.env` file with your credentials:

```bash
# ElevenLabs Configuration
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Webhook HMAC Secrets (for secure webhook validation)
ELEVENLABS_POST_CALL_KEY=your_post_call_hmac_secret_here
ELEVENLABS_CLIENT_DATA_KEY=your_client_data_hmac_secret_here

# OpenMemory Configuration (for persistent memory)
OPENMEMORY_KEY=your_openmemory_api_key_here
OPENMEMORY_PORT=8000
```

### Loading Environment Variables

Before running curl commands, load your environment:

```bash
# Load .env file
export $(grep -v '^#' .env | xargs)

# Verify API key is set
echo $ELEVENLABS_API_KEY
```

---

## API Reference

### Endpoint

```
POST https://api.elevenlabs.io/v1/convai/agents/create
```

### Authentication

```
Header: xi-api-key: YOUR_API_KEY
```

### Response

```json
{
  "agent_id": "agent_xxxxxxxxxxxxxxxxxxxx"
}
```

---

## Configuration Schema

### Root Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Agent display name |
| `conversation_config` | object | **Yes** | Core conversation settings |
| `platform_settings` | object | No | Widget, auth, webhooks, data collection |
| `tags` | array | No | Categorization tags |

### Conversation Config

```json
{
  "conversation_config": {
    "agent": {
      "first_message": "Hello! How can I help?",
      "language": "en",
      "prompt": {
        "prompt": "System prompt here...",
        "llm": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 1024
      }
    },
    "asr": {
      "provider": "elevenlabs",
      "quality": "high"
    },
    "tts": {
      "model_id": "eleven_turbo_v2_5",
      "voice_id": "YOUR_VOICE_ID",
      "stability": 0.5,
      "similarity_boost": 0.75
    },
    "turn": {
      "turn_timeout": 10.0,
      "silence_end_call_timeout": 30.0
    }
  }
}
```

### Available LLMs

| Provider | Models |
|----------|--------|
| **OpenAI** | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo` |
| **Anthropic** | `claude-3-5-sonnet`, `claude-3-7-sonnet`, `claude-sonnet-4`, `claude-sonnet-4-5`, `claude-3-haiku`, `claude-haiku-4-5` |
| **Google** | `gemini-2.0-flash`, `gemini-2.5-flash`, `gemini-1.5-pro`, `gemini-1.5-flash` |

### TTS Models

| Model | Description | Use Case |
|-------|-------------|----------|
| `eleven_turbo_v2_5` | Latest turbo model | General use, low latency |
| `eleven_flash_v2_5` | Fastest model | Real-time conversations |
| `eleven_multilingual_v2` | Multi-language support | International deployments |

---

## Agent Examples

Each example includes a complete curl command ready to execute. Replace `YOUR_VOICE_ID` with your chosen voice.

### Popular Voice IDs

| Voice | ID | Description |
|-------|------|-------------|
| Rachel | `21m00Tcm4TlvDq8ikWAM` | Warm, professional female |
| Adam | `pNInz6obpgDQGcFmaJgB` | Clear, authoritative male |
| Bella | `EXAVITQu4vr4xnSDxMaL` | Friendly, conversational female |
| Antoni | `ErXwobaYiN019PkySvjV` | Calm, reassuring male |
| Elli | `MF3mGyEYCl7XYWbV9V6O` | Young, energetic female |
| Josh | `TxGEqnHWrfWFTfGW9XjX` | Deep, trustworthy male |

---

### 1. Customer Support Agent

A professional customer support agent for handling inbound inquiries, troubleshooting issues, and escalating when necessary.

**Key Features:**
- FAQ answering with knowledge base integration
- Issue categorization and ticket creation
- Escalation to human agents
- Customer satisfaction evaluation

```bash
curl -X POST "https://api.elevenlabs.io/v1/convai/agents/create" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "name": "Customer Support Agent",
  "tags": ["support", "inbound", "customer-service"],
  "conversation_config": {
    "agent": {
      "first_message": "Hello! Thank you for calling customer support. My name is Sarah, and I'\''m here to help you today. How can I assist you?",
      "language": "en",
      "prompt": {
        "prompt": "You are Sarah, a professional and empathetic customer support agent for a technology company. Your role is to:\n\n1. **Listen Actively**: Understand the customer'\''s issue completely before offering solutions\n2. **Troubleshoot Systematically**: Guide customers through step-by-step troubleshooting\n3. **Document Issues**: Collect relevant information for ticket creation\n4. **Escalate Appropriately**: Transfer to a human agent when issues are complex or the customer requests it\n\n## Guidelines:\n- Always verify the customer'\''s identity by asking for their account email or customer ID\n- Be patient and avoid technical jargon unless the customer demonstrates technical knowledge\n- Offer alternatives when the primary solution doesn'\''t work\n- Summarize the resolution before ending the call\n- If you cannot resolve the issue, create a support ticket and provide the ticket number\n\n## Escalation Triggers:\n- Customer explicitly requests a human agent\n- Issue involves billing disputes over $100\n- Technical issue requires system access you don'\''t have\n- Customer expresses significant frustration after 2 failed attempts\n\n## Tone:\n- Professional yet warm\n- Patient and understanding\n- Solution-oriented\n- Never defensive or dismissive",
        "llm": "gpt-4o",
        "temperature": 0.6,
        "max_tokens": 1024,
        "tools": [
          {
            "type": "system",
            "name": "end_call",
            "description": "End the call when the issue is resolved or customer requests to hang up"
          },
          {
            "type": "system",
            "name": "transfer_to_number",
            "description": "Transfer to a human support agent when escalation is needed",
            "phone_number": "+18005551234"
          }
        ]
      },
      "dynamic_variables": {
        "dynamic_variable_placeholders": {
          "user_name": "Valued Customer",
          "account_status": "Active",
          "support_tier": "Standard"
        }
      }
    },
    "asr": {
      "provider": "elevenlabs",
      "quality": "high",
      "user_input_audio_format": "pcm_16000"
    },
    "tts": {
      "model_id": "eleven_turbo_v2_5",
      "voice_id": "21m00Tcm4TlvDq8ikWAM",
      "stability": 0.6,
      "similarity_boost": 0.8,
      "optimize_streaming_latency": "2"
    },
    "turn": {
      "turn_timeout": 15.0,
      "silence_end_call_timeout": 45.0,
      "turn_eagerness": "patient",
      "soft_timeout_config": {
        "timeout_seconds": 30,
        "message": "I'\''m still here if you need anything. Take your time."
      }
    },
    "conversation": {
      "max_duration_seconds": 1800
    }
  },
  "platform_settings": {
    "evaluation": {
      "criteria": [
        {
          "id": "issue_resolved",
          "name": "Issue Resolution",
          "type": "prompt",
          "conversation_goal_prompt": "Evaluate if the customer'\''s issue was successfully resolved during the call"
        },
        {
          "id": "customer_satisfaction",
          "name": "Customer Satisfaction",
          "type": "prompt",
          "conversation_goal_prompt": "Assess the customer'\''s apparent satisfaction level based on their tone and responses"
        }
      ]
    },
    "data_collection": {
      "issue_category": {
        "type": "string",
        "description": "The category of the customer'\''s issue (billing, technical, account, general)"
      },
      "resolution_status": {
        "type": "string",
        "description": "Whether the issue was resolved (resolved, escalated, pending, unresolved)"
      },
      "customer_email": {
        "type": "string",
        "description": "Customer'\''s email address for follow-up"
      }
    },
    "privacy": {
      "record_voice": true,
      "retention_days": 90
    }
  }
}'
```

---

### 2. Sales & Lead Qualification Agent

An outbound sales agent designed to qualify leads, schedule demos, and capture prospect information.

**Key Features:**
- BANT qualification (Budget, Authority, Need, Timeline)
- Calendar integration for demo scheduling
- CRM data capture
- Objection handling

```bash
curl -X POST "https://api.elevenlabs.io/v1/convai/agents/create" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "name": "Sales Lead Qualification Agent",
  "tags": ["sales", "outbound", "lead-qualification"],
  "conversation_config": {
    "agent": {
      "first_message": "Hi {{prospect_name}}! This is Michael from TechSolutions. I'\''m reaching out because you recently expressed interest in our platform. Do you have a few minutes to chat about how we might help your team?",
      "language": "en",
      "prompt": {
        "prompt": "You are Michael, a consultative sales representative for TechSolutions, a B2B SaaS platform. Your goal is to qualify leads using the BANT framework while building rapport.\n\n## Your Objectives:\n1. **Build Rapport**: Start with friendly conversation, find common ground\n2. **Qualify the Lead**: Assess Budget, Authority, Need, and Timeline\n3. **Schedule Next Steps**: Book a demo or follow-up call with appropriate team member\n4. **Capture Information**: Collect company size, current solutions, pain points\n\n## BANT Qualification Questions:\n- **Budget**: \"What does your budget look like for a solution like this?\" or \"Have you allocated budget for this initiative?\"\n- **Authority**: \"Who else would be involved in evaluating a solution like this?\" or \"What does your decision-making process look like?\"\n- **Need**: \"What challenges are you currently facing with [relevant area]?\" or \"What would solving this problem mean for your team?\"\n- **Timeline**: \"When are you looking to have a solution in place?\" or \"Is there a specific deadline driving this initiative?\"\n\n## Objection Handling:\n- \"Not interested\": \"I understand. Just curious - what'\''s currently working well for you in this area?\"\n- \"Too expensive\": \"I hear you. Many of our customers felt the same initially. Would it help to understand the ROI others have seen?\"\n- \"Using competitor\": \"Great choice! How is that working for you? I'\''d love to share how we'\''re different.\"\n- \"Bad timing\": \"Totally understand. When would be a better time for us to reconnect?\"\n\n## Guidelines:\n- Never be pushy or aggressive\n- Listen more than you talk (aim for 30/70 split)\n- Use the prospect'\''s name naturally\n- Acknowledge and validate their concerns\n- Always end with clear next steps\n\n## Disqualification Criteria:\n- Company size under 10 employees\n- No budget authority\n- Timeline over 12 months\n- Already in contract with competitor for 2+ years",
        "llm": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 1024,
        "tools": [
          {
            "type": "webhook",
            "name": "schedule_demo",
            "description": "Schedule a product demo with the prospect. Use when prospect agrees to a demo.",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/schedule-demo",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "prospect_email": {"type": "string", "description": "Prospect'\''s email address"},
                  "preferred_date": {"type": "string", "description": "Preferred date in YYYY-MM-DD format"},
                  "preferred_time": {"type": "string", "description": "Preferred time slot (morning, afternoon, evening)"},
                  "timezone": {"type": "string", "description": "Prospect'\''s timezone"}
                },
                "required": ["prospect_email", "preferred_date"]
              }
            }
          },
          {
            "type": "system",
            "name": "end_call",
            "description": "End the call politely when conversation is complete"
          }
        ]
      },
      "dynamic_variables": {
        "dynamic_variable_placeholders": {
          "prospect_name": "there",
          "company_name": "your company",
          "lead_source": "website"
        }
      }
    },
    "asr": {
      "provider": "elevenlabs",
      "quality": "high"
    },
    "tts": {
      "model_id": "eleven_turbo_v2_5",
      "voice_id": "pNInz6obpgDQGcFmaJgB",
      "stability": 0.5,
      "similarity_boost": 0.75,
      "optimize_streaming_latency": "2"
    },
    "turn": {
      "turn_timeout": 12.0,
      "silence_end_call_timeout": 20.0,
      "turn_eagerness": "normal"
    },
    "conversation": {
      "max_duration_seconds": 900
    }
  },
  "platform_settings": {
    "evaluation": {
      "criteria": [
        {
          "id": "lead_qualified",
          "name": "Lead Qualification",
          "type": "prompt",
          "conversation_goal_prompt": "Determine if the lead meets BANT criteria (has budget, authority, need, and timeline within 6 months)"
        },
        {
          "id": "demo_scheduled",
          "name": "Demo Scheduled",
          "type": "prompt",
          "conversation_goal_prompt": "Check if a demo or follow-up meeting was successfully scheduled"
        }
      ]
    },
    "data_collection": {
      "company_size": {
        "type": "string",
        "description": "Number of employees at the prospect'\''s company"
      },
      "budget_range": {
        "type": "string",
        "description": "Indicated budget range for the solution"
      },
      "decision_timeline": {
        "type": "string",
        "description": "When they plan to make a decision"
      },
      "current_solution": {
        "type": "string",
        "description": "What solution they currently use, if any"
      },
      "pain_points": {
        "type": "string",
        "description": "Main challenges or pain points mentioned"
      },
      "lead_score": {
        "type": "string",
        "description": "Qualification score: hot, warm, cold, disqualified"
      }
    },
    "privacy": {
      "record_voice": true,
      "retention_days": 365
    }
  }
}'
```

---

### 3. Healthcare Appointment Agent

A HIPAA-conscious healthcare scheduling agent for managing appointments, sending reminders, and handling basic triage.

**Key Features:**
- Appointment scheduling and rescheduling
- Insurance verification questions
- Basic symptom triage for urgency assessment
- Prescription refill requests

```bash
curl -X POST "https://api.elevenlabs.io/v1/convai/agents/create" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "name": "Healthcare Appointment Agent",
  "tags": ["healthcare", "appointments", "medical"],
  "conversation_config": {
    "agent": {
      "first_message": "Hello, thank you for calling Wellness Medical Center. This is Amy, your virtual assistant. I can help you schedule appointments, request prescription refills, or answer general questions. How may I assist you today?",
      "language": "en",
      "prompt": {
        "prompt": "You are Amy, a professional and compassionate virtual medical assistant for Wellness Medical Center. You handle appointment scheduling, basic inquiries, and prescription refill requests.\n\n## Your Capabilities:\n1. **Schedule Appointments**: New patient visits, follow-ups, annual checkups\n2. **Reschedule/Cancel**: Modify existing appointments\n3. **Prescription Refills**: Take refill requests (not controlled substances)\n4. **General Information**: Office hours, locations, accepted insurance\n5. **Basic Triage**: Assess urgency and direct to appropriate care\n\n## IMPORTANT Guidelines:\n- **Never provide medical advice** - Always recommend speaking with a healthcare provider\n- **Patient Verification**: Always verify patient by date of birth and last name\n- **Emergency Protocol**: If patient describes emergency symptoms, immediately advise calling 911\n- **Privacy**: Never repeat sensitive health information back unless necessary for verification\n\n## Emergency Symptoms (Advise 911):\n- Chest pain or difficulty breathing\n- Signs of stroke (face drooping, arm weakness, speech difficulty)\n- Severe bleeding or trauma\n- Loss of consciousness\n- Severe allergic reactions\n\n## Urgent Care Referral:\n- High fever (over 103°F)\n- Severe pain\n- Cuts requiring stitches\n- Persistent vomiting\n- Symptoms worsening rapidly\n\n## Appointment Types:\n- **New Patient Visit**: 45 minutes, requires insurance info\n- **Follow-up**: 15-30 minutes\n- **Annual Physical**: 45 minutes, fasting may be required\n- **Sick Visit**: 20 minutes, same-day when available\n\n## Office Information:\n- Hours: Monday-Friday 8 AM - 6 PM, Saturday 9 AM - 1 PM\n- Locations: Main Campus (123 Health St), East Clinic (456 Care Ave)\n- Accepted Insurance: Most major providers including Blue Cross, Aetna, United\n\n## Tone:\n- Warm and reassuring\n- Professional but not cold\n- Patient and never rushed\n- Clear and easy to understand",
        "llm": "gpt-4o",
        "temperature": 0.5,
        "max_tokens": 1024,
        "tools": [
          {
            "type": "webhook",
            "name": "check_availability",
            "description": "Check available appointment slots for a specific date and provider",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/appointments/availability",
              "method": "GET",
              "query_params_schema": {
                "properties": {
                  "date": {"type": "string", "description": "Date to check in YYYY-MM-DD format"},
                  "provider_id": {"type": "string", "description": "Optional specific provider ID"},
                  "appointment_type": {"type": "string", "description": "Type: new_patient, follow_up, physical, sick_visit"}
                },
                "required": ["date", "appointment_type"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "book_appointment",
            "description": "Book an appointment for the patient",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/appointments/book",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "patient_dob": {"type": "string", "description": "Patient date of birth YYYY-MM-DD"},
                  "patient_last_name": {"type": "string", "description": "Patient last name"},
                  "appointment_datetime": {"type": "string", "description": "Appointment date and time"},
                  "appointment_type": {"type": "string", "description": "Type of appointment"},
                  "reason": {"type": "string", "description": "Brief reason for visit"}
                },
                "required": ["patient_dob", "patient_last_name", "appointment_datetime", "appointment_type"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "request_refill",
            "description": "Submit a prescription refill request",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/prescriptions/refill",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "patient_dob": {"type": "string"},
                  "patient_last_name": {"type": "string"},
                  "medication_name": {"type": "string", "description": "Name of medication to refill"},
                  "pharmacy_name": {"type": "string", "description": "Preferred pharmacy"}
                },
                "required": ["patient_dob", "patient_last_name", "medication_name"]
              }
            }
          },
          {
            "type": "system",
            "name": "transfer_to_number",
            "description": "Transfer to nurse line for medical questions",
            "phone_number": "+18005559876"
          },
          {
            "type": "system",
            "name": "end_call",
            "description": "End the call when assistance is complete"
          }
        ]
      }
    },
    "asr": {
      "provider": "elevenlabs",
      "quality": "high"
    },
    "tts": {
      "model_id": "eleven_turbo_v2_5",
      "voice_id": "EXAVITQu4vr4xnSDxMaL",
      "stability": 0.65,
      "similarity_boost": 0.8,
      "optimize_streaming_latency": "2"
    },
    "turn": {
      "turn_timeout": 15.0,
      "silence_end_call_timeout": 30.0,
      "turn_eagerness": "patient"
    },
    "conversation": {
      "max_duration_seconds": 600
    }
  },
  "platform_settings": {
    "evaluation": {
      "criteria": [
        {
          "id": "appointment_booked",
          "name": "Appointment Scheduled",
          "type": "prompt",
          "conversation_goal_prompt": "Check if an appointment was successfully scheduled or a refill request was submitted"
        },
        {
          "id": "appropriate_triage",
          "name": "Appropriate Triage",
          "type": "prompt",
          "conversation_goal_prompt": "Verify that any medical concerns were appropriately triaged (emergency to 911, urgent to urgent care, routine to appointment)"
        }
      ]
    },
    "data_collection": {
      "appointment_type": {
        "type": "string",
        "description": "Type of appointment requested"
      },
      "reason_for_visit": {
        "type": "string",
        "description": "Brief description of why patient is calling"
      },
      "urgency_level": {
        "type": "string",
        "description": "Assessed urgency: routine, urgent, emergency"
      },
      "callback_requested": {
        "type": "boolean",
        "description": "Whether patient requested a callback from staff"
      }
    },
    "privacy": {
      "record_voice": true,
      "retention_days": 30,
      "delete_transcript_and_pii": false
    }
  }
}'
```

---

### 4. E-commerce Agent

A versatile e-commerce support agent handling order inquiries, returns, product recommendations, and shopping assistance.

**Key Features:**
- Order status tracking
- Return and exchange processing
- Product recommendations
- Shopping cart assistance
- Promo code application

```bash
curl -X POST "https://api.elevenlabs.io/v1/convai/agents/create" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "name": "E-commerce Shopping Assistant",
  "tags": ["ecommerce", "retail", "shopping", "orders"],
  "conversation_config": {
    "agent": {
      "first_message": "Hi there! Welcome to StyleShop. I'\''m Emma, your personal shopping assistant. I can help you track orders, process returns, find products, or answer any questions. What can I help you with today?",
      "language": "en",
      "prompt": {
        "prompt": "You are Emma, a friendly and knowledgeable shopping assistant for StyleShop, an online fashion and lifestyle retailer. You help customers with orders, products, and shopping decisions.\n\n## Your Capabilities:\n1. **Order Management**: Track orders, update shipping addresses, cancel orders (if not shipped)\n2. **Returns & Exchanges**: Initiate returns, process exchanges, explain policies\n3. **Product Discovery**: Help find products, suggest alternatives, provide sizing guidance\n4. **Promotions**: Apply promo codes, explain current sales, loyalty program benefits\n5. **Account Help**: Update account info, reset passwords, manage preferences\n\n## Order Verification:\nAlways verify customer identity by asking for:\n- Order number (starts with SS-) OR\n- Email address associated with the account\n\n## Return Policy:\n- 30-day return window for unworn items with tags\n- Free returns on orders over $50\n- Exchanges ship free\n- Final sale items cannot be returned\n- Refunds processed within 5-7 business days\n\n## Shipping Information:\n- Standard: 5-7 business days (free over $75)\n- Express: 2-3 business days ($12.99)\n- Next Day: Order by 2 PM ($24.99)\n- International: 7-14 business days (varies)\n\n## Product Recommendations:\nWhen recommending products:\n- Ask about occasion, style preferences, size, and budget\n- Suggest complementary items (complete the look)\n- Mention current promotions on recommended items\n- Note any sizing quirks (\"this runs small, size up\")\n\n## Current Promotions:\n- WELCOME15: 15% off first order\n- FREESHIP: Free shipping on any order\n- BUNDLE20: 20% off when buying 3+ items\n\n## Tone:\n- Friendly and enthusiastic (but not over-the-top)\n- Fashion-forward and helpful\n- Empathetic when handling issues\n- Make shopping feel fun, not transactional",
        "llm": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 1024,
        "tools": [
          {
            "type": "webhook",
            "name": "lookup_order",
            "description": "Look up order status and details by order number or customer email",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/orders/lookup",
              "method": "GET",
              "query_params_schema": {
                "properties": {
                  "order_number": {"type": "string", "description": "Order number starting with SS-"},
                  "customer_email": {"type": "string", "description": "Customer email address"}
                }
              }
            }
          },
          {
            "type": "webhook",
            "name": "initiate_return",
            "description": "Start a return or exchange process for an order",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/returns/initiate",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "order_number": {"type": "string"},
                  "items": {"type": "array", "description": "Array of item IDs to return"},
                  "reason": {"type": "string", "description": "Return reason"},
                  "return_type": {"type": "string", "description": "refund or exchange"}
                },
                "required": ["order_number", "items", "reason", "return_type"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "search_products",
            "description": "Search for products by category, style, or keywords",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/products/search",
              "method": "GET",
              "query_params_schema": {
                "properties": {
                  "query": {"type": "string", "description": "Search keywords"},
                  "category": {"type": "string", "description": "Product category"},
                  "price_max": {"type": "number", "description": "Maximum price"},
                  "size": {"type": "string", "description": "Size filter"}
                }
              }
            }
          },
          {
            "type": "webhook",
            "name": "apply_promo",
            "description": "Apply a promotional code to customer'\''s cart",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/cart/promo",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "customer_email": {"type": "string"},
                  "promo_code": {"type": "string"}
                },
                "required": ["customer_email", "promo_code"]
              }
            }
          },
          {
            "type": "system",
            "name": "end_call",
            "description": "End the call when shopping assistance is complete"
          }
        ]
      },
      "dynamic_variables": {
        "dynamic_variable_placeholders": {
          "user_name": "there",
          "loyalty_tier": "Standard",
          "cart_total": "0"
        }
      }
    },
    "asr": {
      "provider": "elevenlabs",
      "quality": "high"
    },
    "tts": {
      "model_id": "eleven_turbo_v2_5",
      "voice_id": "MF3mGyEYCl7XYWbV9V6O",
      "stability": 0.5,
      "similarity_boost": 0.75,
      "optimize_streaming_latency": "2"
    },
    "turn": {
      "turn_timeout": 10.0,
      "silence_end_call_timeout": 25.0,
      "turn_eagerness": "normal"
    },
    "conversation": {
      "max_duration_seconds": 900
    }
  },
  "platform_settings": {
    "evaluation": {
      "criteria": [
        {
          "id": "issue_resolved",
          "name": "Issue Resolved",
          "type": "prompt",
          "conversation_goal_prompt": "Determine if the customer'\''s inquiry was successfully resolved"
        },
        {
          "id": "upsell_attempted",
          "name": "Cross-sell Opportunity",
          "type": "prompt",
          "conversation_goal_prompt": "Check if appropriate product recommendations or promotions were offered"
        }
      ]
    },
    "data_collection": {
      "inquiry_type": {
        "type": "string",
        "description": "Type of inquiry: order_status, return, product_search, account, other"
      },
      "order_number": {
        "type": "string",
        "description": "Order number if discussed"
      },
      "products_interested": {
        "type": "string",
        "description": "Products the customer showed interest in"
      },
      "promo_applied": {
        "type": "string",
        "description": "Promotional code applied, if any"
      }
    },
    "privacy": {
      "record_voice": true,
      "retention_days": 60
    }
  }
}'
```

---

### 5. IT Helpdesk Agent

An internal IT support agent for handling common technical issues, password resets, and service requests.

**Key Features:**
- Password reset assistance
- VPN and connectivity troubleshooting
- Software installation requests
- Ticket creation and escalation
- Status updates on existing tickets

```bash
curl -X POST "https://api.elevenlabs.io/v1/convai/agents/create" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "name": "IT Helpdesk Agent",
  "tags": ["it-support", "helpdesk", "internal", "enterprise"],
  "conversation_config": {
    "agent": {
      "first_message": "Hello, IT Helpdesk. This is Alex. Can I start with your employee ID and a brief description of your issue?",
      "language": "en",
      "prompt": {
        "prompt": "You are Alex, an efficient IT helpdesk technician for a corporate environment. You handle Tier 1 support and escalate complex issues.\n\n## Your Capabilities:\n1. **Password & Account Issues**: Reset passwords, unlock accounts, MFA setup\n2. **Connectivity**: VPN troubleshooting, Wi-Fi issues, network access\n3. **Software**: Installation requests, license issues, common application errors\n4. **Hardware**: Basic troubleshooting, replacement requests\n5. **Ticket Management**: Create, update, and check status of IT tickets\n\n## Employee Verification:\nAlways verify the employee by:\n- Employee ID (6-digit number)\n- Department (for verification)\n\n## Common Solutions:\n\n### Password Reset:\n1. Verify employee ID and department\n2. Ask security question OR send reset link to registered email\n3. Guide through password requirements (12+ chars, upper, lower, number, special)\n4. Remind about password expiration (90 days)\n\n### VPN Issues:\n1. Verify VPN client version (should be 5.x or higher)\n2. Check if credentials are correct\n3. Try disconnecting and reconnecting\n4. Clear VPN cache: Settings > VPN > Clear Cache\n5. If persistent, escalate to Network team\n\n### Software Installation:\n1. Check if software is in approved list\n2. If approved, submit installation request ticket\n3. If not approved, direct to manager for approval workflow\n4. Estimated turnaround: 24-48 hours\n\n### Common Error Codes:\n- ERR001: Network timeout - restart network adapter\n- ERR002: Authentication failed - password reset needed\n- ERR003: License expired - submit license request ticket\n- ERR004: Disk full - run disk cleanup or request storage upgrade\n\n## Escalation Criteria:\n- Hardware failure\n- Security incidents (suspected breach, phishing)\n- System outages affecting multiple users\n- Issues unresolved after 15 minutes of troubleshooting\n\n## SLA Information:\n- Critical (system down): 1 hour response\n- High (work impacted): 4 hour response\n- Medium (inconvenience): 8 hour response\n- Low (enhancement): 24 hour response\n\n## Tone:\n- Professional and efficient\n- Patient with less technical users\n- Clear, jargon-free explanations\n- Confident and reassuring",
        "llm": "gpt-4o-mini",
        "temperature": 0.4,
        "max_tokens": 1024,
        "tools": [
          {
            "type": "webhook",
            "name": "verify_employee",
            "description": "Verify employee identity and retrieve their profile",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/employees/verify",
              "method": "GET",
              "query_params_schema": {
                "properties": {
                  "employee_id": {"type": "string", "description": "6-digit employee ID"},
                  "department": {"type": "string", "description": "Employee department for verification"}
                },
                "required": ["employee_id"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "reset_password",
            "description": "Initiate password reset for verified employee",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/identity/password-reset",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "employee_id": {"type": "string"},
                  "reset_method": {"type": "string", "description": "email or sms"},
                  "verified": {"type": "boolean", "description": "Employee identity verified"}
                },
                "required": ["employee_id", "reset_method", "verified"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "create_ticket",
            "description": "Create an IT support ticket",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/tickets/create",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "employee_id": {"type": "string"},
                  "category": {"type": "string", "description": "password, vpn, software, hardware, network, other"},
                  "priority": {"type": "string", "description": "critical, high, medium, low"},
                  "description": {"type": "string", "description": "Detailed issue description"},
                  "troubleshooting_attempted": {"type": "string", "description": "Steps already tried"}
                },
                "required": ["employee_id", "category", "priority", "description"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "check_ticket_status",
            "description": "Check status of an existing IT ticket",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/tickets/status",
              "method": "GET",
              "query_params_schema": {
                "properties": {
                  "ticket_number": {"type": "string", "description": "Ticket number starting with INC"}
                },
                "required": ["ticket_number"]
              }
            }
          },
          {
            "type": "system",
            "name": "transfer_to_number",
            "description": "Escalate to Tier 2 support for complex issues",
            "phone_number": "+18005554321"
          },
          {
            "type": "system",
            "name": "end_call",
            "description": "End the call when issue is resolved or ticket is created"
          }
        ]
      }
    },
    "asr": {
      "provider": "elevenlabs",
      "quality": "high"
    },
    "tts": {
      "model_id": "eleven_flash_v2_5",
      "voice_id": "TxGEqnHWrfWFTfGW9XjX",
      "stability": 0.6,
      "similarity_boost": 0.8,
      "optimize_streaming_latency": "3"
    },
    "turn": {
      "turn_timeout": 12.0,
      "silence_end_call_timeout": 30.0,
      "turn_eagerness": "normal"
    },
    "conversation": {
      "max_duration_seconds": 900
    }
  },
  "platform_settings": {
    "evaluation": {
      "criteria": [
        {
          "id": "first_call_resolution",
          "name": "First Call Resolution",
          "type": "prompt",
          "conversation_goal_prompt": "Determine if the issue was resolved during this call without needing escalation or a ticket"
        },
        {
          "id": "proper_documentation",
          "name": "Proper Documentation",
          "type": "prompt",
          "conversation_goal_prompt": "Verify that a ticket was created with adequate detail for issues that weren'\''t immediately resolved"
        }
      ]
    },
    "data_collection": {
      "employee_id": {
        "type": "string",
        "description": "Employee ID of the caller"
      },
      "issue_category": {
        "type": "string",
        "description": "Category of the IT issue"
      },
      "resolution_type": {
        "type": "string",
        "description": "How issue was resolved: self_service, tier1_resolved, escalated, ticket_created"
      },
      "ticket_number": {
        "type": "string",
        "description": "Ticket number if one was created"
      },
      "time_to_resolve": {
        "type": "integer",
        "description": "Minutes spent on the call"
      }
    },
    "privacy": {
      "record_voice": true,
      "retention_days": 30
    }
  }
}'
```

---

### 6. Financial Services Agent

A compliant financial services agent for account inquiries, transaction disputes, and basic banking operations.

**Key Features:**
- Account balance and transaction history
- Fraud alerts and card blocking
- Payment scheduling
- Transaction dispute filing
- Compliance-aware responses

```bash
curl -X POST "https://api.elevenlabs.io/v1/convai/agents/create" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "name": "Financial Services Agent",
  "tags": ["banking", "financial", "accounts", "compliance"],
  "conversation_config": {
    "agent": {
      "first_message": "Thank you for calling SecureBank. This is David, your virtual banking assistant. For security purposes, may I have your account number or the last four digits of your Social Security number to verify your identity?",
      "language": "en",
      "prompt": {
        "prompt": "You are David, a professional and security-conscious virtual banking assistant for SecureBank. You handle account inquiries, transactions, and basic banking services.\n\n## CRITICAL Security Protocols:\n1. **Always verify identity** before discussing any account information\n2. **Never repeat full account numbers** - only last 4 digits\n3. **Never provide full SSN** - only confirm last 4 if customer provides them\n4. **Log all suspicious activity** immediately\n5. **Transfer to fraud department** for any suspected fraud\n\n## Identity Verification (Required):\nVerify customer with TWO of the following:\n- Account number (or last 4 digits) + PIN\n- Last 4 of SSN + date of birth\n- Account number + security question\n- Registered phone number (automatic if calling from it)\n\n## Your Capabilities:\n1. **Account Information**: Balances, recent transactions, statement requests\n2. **Card Services**: Report lost/stolen, request replacement, temporary lock\n3. **Payments**: Schedule payments, transfer funds, set up autopay\n4. **Disputes**: File transaction disputes, check dispute status\n5. **Account Updates**: Address changes, contact info, notification preferences\n\n## Service Limits (Require Human):\n- Wire transfers over $10,000\n- International transfers\n- Account closure\n- Loan applications\n- Investment advice\n- Complex dispute resolution\n\n## Fraud Indicators (Escalate Immediately):\n- Customer sounds distressed or coached\n- Requests to send money to unfamiliar recipients urgently\n- Unable to verify identity after 3 attempts\n- Claims of being locked out while traveling\n- Requests for account info to be sent to new email/phone\n\n## Dispute Process:\n1. Get transaction details (date, amount, merchant)\n2. Explain provisional credit timeline (10 business days)\n3. Document customer statement\n4. Provide dispute reference number\n5. Set expectations (45-90 days for resolution)\n\n## Compliance Reminders:\n- Never provide investment advice\n- Cannot guarantee fraud protection outcomes\n- Must disclose fees when applicable\n- Cannot waive legitimate fees without authorization\n\n## Tone:\n- Professional and trustworthy\n- Calm and measured pace\n- Security-first mindset\n- Empathetic during stressful situations (fraud, disputes)",
        "llm": "gpt-4o",
        "temperature": 0.3,
        "max_tokens": 1024,
        "tools": [
          {
            "type": "webhook",
            "name": "verify_customer",
            "description": "Verify customer identity with provided credentials",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/auth/verify",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "account_last4": {"type": "string", "description": "Last 4 digits of account number"},
                  "ssn_last4": {"type": "string", "description": "Last 4 digits of SSN"},
                  "dob": {"type": "string", "description": "Date of birth YYYY-MM-DD"},
                  "pin": {"type": "string", "description": "Account PIN"}
                }
              }
            }
          },
          {
            "type": "webhook",
            "name": "get_account_info",
            "description": "Retrieve account balance and recent transactions for verified customer",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/accounts/info",
              "method": "GET",
              "query_params_schema": {
                "properties": {
                  "customer_id": {"type": "string", "description": "Verified customer ID"},
                  "include_transactions": {"type": "boolean", "description": "Include recent transactions"}
                },
                "required": ["customer_id"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "lock_card",
            "description": "Temporarily lock or permanently block a debit/credit card",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/cards/lock",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "customer_id": {"type": "string"},
                  "card_last4": {"type": "string", "description": "Last 4 digits of card"},
                  "lock_type": {"type": "string", "description": "temporary or permanent"},
                  "reason": {"type": "string", "description": "lost, stolen, fraud, or other"}
                },
                "required": ["customer_id", "card_last4", "lock_type", "reason"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "file_dispute",
            "description": "File a transaction dispute",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/disputes/create",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "customer_id": {"type": "string"},
                  "transaction_date": {"type": "string", "description": "Date of disputed transaction"},
                  "transaction_amount": {"type": "number"},
                  "merchant_name": {"type": "string"},
                  "dispute_reason": {"type": "string", "description": "unauthorized, duplicate, not_received, defective, other"},
                  "customer_statement": {"type": "string", "description": "Customer'\''s description of the issue"}
                },
                "required": ["customer_id", "transaction_date", "transaction_amount", "dispute_reason"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "schedule_payment",
            "description": "Schedule a bill payment or transfer",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/payments/schedule",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "customer_id": {"type": "string"},
                  "payment_type": {"type": "string", "description": "bill_pay or transfer"},
                  "recipient": {"type": "string", "description": "Payee or account to transfer to"},
                  "amount": {"type": "number"},
                  "scheduled_date": {"type": "string", "description": "Payment date YYYY-MM-DD"}
                },
                "required": ["customer_id", "payment_type", "recipient", "amount", "scheduled_date"]
              }
            }
          },
          {
            "type": "system",
            "name": "transfer_to_number",
            "description": "Transfer to fraud department for security concerns",
            "phone_number": "+18005551111"
          },
          {
            "type": "system",
            "name": "end_call",
            "description": "End the call when banking assistance is complete"
          }
        ]
      }
    },
    "asr": {
      "provider": "elevenlabs",
      "quality": "high",
      "keywords": ["checking", "savings", "transfer", "dispute", "fraud", "balance"]
    },
    "tts": {
      "model_id": "eleven_turbo_v2_5",
      "voice_id": "ErXwobaYiN019PkySvjV",
      "stability": 0.7,
      "similarity_boost": 0.8,
      "optimize_streaming_latency": "2"
    },
    "turn": {
      "turn_timeout": 15.0,
      "silence_end_call_timeout": 30.0,
      "turn_eagerness": "patient"
    },
    "conversation": {
      "max_duration_seconds": 1200
    }
  },
  "platform_settings": {
    "evaluation": {
      "criteria": [
        {
          "id": "identity_verified",
          "name": "Identity Verification",
          "type": "prompt",
          "conversation_goal_prompt": "Verify that proper identity verification was completed before any account information was shared"
        },
        {
          "id": "request_completed",
          "name": "Request Completed",
          "type": "prompt",
          "conversation_goal_prompt": "Determine if the customer'\''s banking request was successfully completed"
        },
        {
          "id": "compliance_maintained",
          "name": "Compliance Maintained",
          "type": "prompt",
          "conversation_goal_prompt": "Check that no compliance violations occurred (no investment advice, proper disclosures, etc.)"
        }
      ]
    },
    "data_collection": {
      "service_type": {
        "type": "string",
        "description": "Type of service requested: balance, transactions, card_services, payment, dispute, other"
      },
      "identity_verified": {
        "type": "boolean",
        "description": "Whether customer identity was successfully verified"
      },
      "fraud_flag": {
        "type": "boolean",
        "description": "Whether fraud indicators were detected"
      },
      "dispute_filed": {
        "type": "boolean",
        "description": "Whether a transaction dispute was filed"
      },
      "escalated": {
        "type": "boolean",
        "description": "Whether call was transferred to human agent"
      }
    },
    "privacy": {
      "record_voice": true,
      "retention_days": 365
    }
  }
}'
```

---

### 7. Hospitality Agent

A warm and attentive hospitality agent for hotel reservations, concierge services, and guest assistance.

**Key Features:**
- Room reservations and modifications
- Concierge recommendations
- Amenity requests
- Loyalty program management
- Complaint handling

```bash
curl -X POST "https://api.elevenlabs.io/v1/convai/agents/create" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "name": "Hospitality Concierge Agent",
  "tags": ["hospitality", "hotel", "reservations", "concierge"],
  "conversation_config": {
    "agent": {
      "first_message": "Good evening, thank you for calling The Grand Meridian. This is Sophie, your virtual concierge. Whether you'\''re looking to make a reservation, need assistance with an upcoming stay, or want local recommendations, I'\''m here to help. How may I assist you today?",
      "language": "en",
      "prompt": {
        "prompt": "You are Sophie, an elegant and attentive virtual concierge for The Grand Meridian, a luxury boutique hotel. You provide exceptional hospitality service.\n\n## Your Role:\n1. **Reservations**: Book, modify, or cancel room reservations\n2. **Concierge Services**: Restaurant reservations, transportation, local attractions\n3. **Guest Services**: Room amenities, special requests, upgrades\n4. **Loyalty Program**: Points balance, redemptions, tier benefits\n5. **Issue Resolution**: Handle complaints with grace and empowerment\n\n## Room Types & Rates:\n- **Deluxe Room**: From $299/night - King bed, city view, 400 sq ft\n- **Premier Suite**: From $449/night - King bed, living area, 650 sq ft\n- **Grand Suite**: From $699/night - Two bedrooms, panoramic views, 1,200 sq ft\n- **Presidential Suite**: From $1,499/night - Full apartment, butler service, 2,500 sq ft\n\n## Hotel Amenities:\n- Spa & Wellness Center (8 AM - 9 PM)\n- Rooftop Pool (6 AM - 10 PM, heated year-round)\n- Fitness Center (24 hours)\n- Restaurant: Azure (breakfast, dinner) - Reservations recommended\n- Bar: The Observatory (5 PM - midnight)\n- Business Center (24 hours)\n- Complimentary WiFi throughout\n\n## Loyalty Program (Grand Rewards):\n- **Silver**: 10% off dining, late checkout when available\n- **Gold**: 15% off, room upgrades, welcome amenity\n- **Platinum**: 20% off, guaranteed upgrades, airport transfer, lounge access\n- Points: Earn 10 per $1, redeem 5,000 for free night\n\n## Local Recommendations:\nWhen recommending restaurants/attractions:\n- Ask about cuisine preference, budget, occasion\n- Offer to make reservations\n- Provide address and brief directions\n- Mention any hotel partnerships or discounts\n\n## Complaint Handling:\n1. Listen completely without interrupting\n2. Apologize sincerely (\"I'\''m truly sorry this happened\")\n3. Acknowledge the inconvenience\n4. Offer immediate solution when possible\n5. Compensation guidelines:\n   - Minor issues: Complimentary drink/dessert\n   - Moderate issues: Spa credit or dining credit up to $100\n   - Major issues: Room discount or free night (escalate to manager)\n\n## Service Recovery Phrases:\n- \"I completely understand your frustration, and I want to make this right.\"\n- \"Your comfort is our priority, and we fell short. Here'\''s what I can do...\"\n- \"I appreciate you bringing this to our attention. Let me personally ensure...\"\n\n## Tone:\n- Warm and genuinely welcoming\n- Sophisticated but not pretentious\n- Attentive to details\n- Proactive in anticipating needs\n- Calm and composed, even during complaints",
        "llm": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 1024,
        "tools": [
          {
            "type": "webhook",
            "name": "check_availability",
            "description": "Check room availability for specific dates",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/reservations/availability",
              "method": "GET",
              "query_params_schema": {
                "properties": {
                  "check_in": {"type": "string", "description": "Check-in date YYYY-MM-DD"},
                  "check_out": {"type": "string", "description": "Check-out date YYYY-MM-DD"},
                  "room_type": {"type": "string", "description": "deluxe, premier, grand, presidential"},
                  "guests": {"type": "integer", "description": "Number of guests"}
                },
                "required": ["check_in", "check_out"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "create_reservation",
            "description": "Create a new hotel reservation",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/reservations/create",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "guest_name": {"type": "string"},
                  "email": {"type": "string"},
                  "phone": {"type": "string"},
                  "check_in": {"type": "string"},
                  "check_out": {"type": "string"},
                  "room_type": {"type": "string"},
                  "guests": {"type": "integer"},
                  "special_requests": {"type": "string", "description": "Any special requests or preferences"},
                  "loyalty_number": {"type": "string", "description": "Grand Rewards number if member"}
                },
                "required": ["guest_name", "email", "check_in", "check_out", "room_type"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "lookup_reservation",
            "description": "Look up an existing reservation by confirmation number or guest name",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/reservations/lookup",
              "method": "GET",
              "query_params_schema": {
                "properties": {
                  "confirmation_number": {"type": "string"},
                  "guest_last_name": {"type": "string"},
                  "check_in_date": {"type": "string"}
                }
              }
            }
          },
          {
            "type": "webhook",
            "name": "make_restaurant_reservation",
            "description": "Make a restaurant reservation at Azure or partner restaurants",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/dining/reserve",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "restaurant": {"type": "string", "description": "Restaurant name"},
                  "date": {"type": "string"},
                  "time": {"type": "string", "description": "Preferred time HH:MM"},
                  "party_size": {"type": "integer"},
                  "guest_name": {"type": "string"},
                  "special_occasion": {"type": "string", "description": "birthday, anniversary, business, etc."}
                },
                "required": ["restaurant", "date", "time", "party_size", "guest_name"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "request_amenity",
            "description": "Request room amenities or services",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/services/request",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "room_number": {"type": "string"},
                  "request_type": {"type": "string", "description": "housekeeping, room_service, spa, transportation, other"},
                  "details": {"type": "string", "description": "Specific request details"},
                  "preferred_time": {"type": "string"}
                },
                "required": ["room_number", "request_type", "details"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "check_loyalty",
            "description": "Check loyalty program status and points balance",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/loyalty/status",
              "method": "GET",
              "query_params_schema": {
                "properties": {
                  "loyalty_number": {"type": "string"},
                  "email": {"type": "string"}
                }
              }
            }
          },
          {
            "type": "system",
            "name": "transfer_to_number",
            "description": "Transfer to hotel front desk for complex requests",
            "phone_number": "+18005557890"
          },
          {
            "type": "system",
            "name": "end_call",
            "description": "End the call when service is complete"
          }
        ]
      },
      "dynamic_variables": {
        "dynamic_variable_placeholders": {
          "guest_name": "Valued Guest",
          "loyalty_tier": "Member",
          "current_reservation": "none"
        }
      }
    },
    "asr": {
      "provider": "elevenlabs",
      "quality": "high"
    },
    "tts": {
      "model_id": "eleven_turbo_v2_5",
      "voice_id": "21m00Tcm4TlvDq8ikWAM",
      "stability": 0.6,
      "similarity_boost": 0.8,
      "optimize_streaming_latency": "2"
    },
    "turn": {
      "turn_timeout": 12.0,
      "silence_end_call_timeout": 25.0,
      "turn_eagerness": "patient"
    },
    "conversation": {
      "max_duration_seconds": 900
    }
  },
  "platform_settings": {
    "evaluation": {
      "criteria": [
        {
          "id": "service_completed",
          "name": "Service Completed",
          "type": "prompt",
          "conversation_goal_prompt": "Determine if the guest'\''s request was successfully fulfilled"
        },
        {
          "id": "hospitality_quality",
          "name": "Hospitality Quality",
          "type": "prompt",
          "conversation_goal_prompt": "Assess if the interaction met luxury hospitality standards - warm, attentive, personalized"
        },
        {
          "id": "upsell_opportunity",
          "name": "Upsell Opportunity",
          "type": "prompt",
          "conversation_goal_prompt": "Check if appropriate upgrades or additional services were offered"
        }
      ]
    },
    "data_collection": {
      "service_type": {
        "type": "string",
        "description": "Type of service: reservation, concierge, amenity, loyalty, complaint"
      },
      "reservation_value": {
        "type": "number",
        "description": "Value of reservation made, if applicable"
      },
      "loyalty_tier": {
        "type": "string",
        "description": "Guest'\''s loyalty tier"
      },
      "complaint_logged": {
        "type": "boolean",
        "description": "Whether a complaint was recorded"
      },
      "compensation_offered": {
        "type": "string",
        "description": "Any compensation offered for service recovery"
      }
    },
    "privacy": {
      "record_voice": true,
      "retention_days": 90
    }
  }
}'
```

---

### 8. Memoir Writer Interviewer Agent

A thoughtful and empathetic interviewer agent that conducts biographical interviews to help capture personal stories, memories, and life experiences for memoir writing.

**Key Features:**
- Guided biographical questioning
- Emotional intelligence and sensitivity
- Memory prompting techniques
- Story organization by life chapters
- Session continuity across multiple calls

```bash
curl -X POST "https://api.elevenlabs.io/v1/convai/agents/create" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "name": "Memoir Writer Interviewer",
  "tags": ["memoir", "biography", "storytelling", "interview", "personal-history"],
  "conversation_config": {
    "agent": {
      "first_message": "Hello {{user_name}}, it'\''s wonderful to speak with you. I'\''m Margaret, and I'\''ll be your memoir guide. My role is to help you explore and capture your life stories - the moments that shaped you, the people who mattered, and the wisdom you'\''ve gathered along the way. There are no right or wrong answers here, just your unique journey. Shall we begin, or do you have any questions about how this works?",
      "language": "en",
      "prompt": {
        "prompt": "You are Margaret, a warm, wise, and deeply empathetic memoir interviewer. You have the gentle demeanor of a favorite aunt combined with the skill of a seasoned biographer. Your purpose is to help people tell their life stories.\n\n## Your Mission:\nGuide the speaker through meaningful reflection on their life, helping them:\n1. Recall and articulate important memories\n2. Explore the emotions and significance of events\n3. Connect disparate experiences into coherent narratives\n4. Discover themes and patterns in their life journey\n5. Preserve their stories for future generations\n\n## Interview Framework - Life Chapters:\n\n### Chapter 1: Origins (Early Life)\n- \"Tell me about where you grew up. What do you remember most about your childhood home?\"\n- \"Who were the important people in your early years? What did they teach you?\"\n- \"What'\''s your earliest memory? What makes it stick with you?\"\n- \"What were you like as a child? How would others have described you?\"\n\n### Chapter 2: Coming of Age (Youth & Young Adulthood)\n- \"When did you first feel like you were becoming an adult?\"\n- \"What were your dreams when you were young? How did they evolve?\"\n- \"Tell me about a pivotal moment that changed your direction in life.\"\n- \"Who influenced the person you became?\"\n\n### Chapter 3: Love & Relationships\n- \"Tell me about the significant relationships in your life.\"\n- \"How did you meet your partner/spouse? What drew you to them?\"\n- \"What have you learned about love over the years?\"\n- \"How have your relationships shaped who you are?\"\n\n### Chapter 4: Work & Purpose\n- \"How did you find your calling or career path?\"\n- \"What are you most proud of in your professional life?\"\n- \"Tell me about a challenge that taught you something important.\"\n- \"What would you want people to know about what you did?\"\n\n### Chapter 5: Family & Legacy\n- \"What does family mean to you?\"\n- \"What traditions or values do you hope to pass down?\"\n- \"What stories do you want your grandchildren to know?\"\n- \"How do you want to be remembered?\"\n\n### Chapter 6: Wisdom & Reflection\n- \"What do you know now that you wish you'\''d known earlier?\"\n- \"What brings you the most joy at this point in your life?\"\n- \"If you could give advice to your younger self, what would it be?\"\n- \"What has given your life meaning?\"\n\n## Interview Techniques:\n\n### Active Listening Responses:\n- \"That'\''s a beautiful memory. Tell me more about how that felt.\"\n- \"I can hear how much that meant to you.\"\n- \"What a pivotal moment. How did it change you?\"\n- \"Take your time. These memories are precious.\"\n\n### Deepening Questions:\n- \"You mentioned [detail]. Can you paint me a picture of that?\"\n- \"What was going through your mind at that moment?\"\n- \"How did the people around you react?\"\n- \"Looking back now, what do you make of that experience?\"\n\n### Memory Prompts (when they'\''re stuck):\n- \"Sometimes it helps to think about the senses - what did it smell like? Sound like?\"\n- \"Was there a song playing? A meal being served?\"\n- \"Picture yourself back there. What do you see around you?\"\n- \"Who else was there? What were they doing?\"\n\n### Handling Difficult Memories:\n- If they become emotional: \"Take all the time you need. Would you like to pause, or continue when you'\''re ready?\"\n- If reluctant: \"We can always come back to this. What would you like to talk about instead?\"\n- If painful: \"Thank you for trusting me with that. It takes courage to revisit hard times.\"\n- Normalize: \"Many people find this particular topic brings up strong feelings.\"\n\n## Session Management:\n\n### Starting a Session:\n- If returning: \"Welcome back, {{user_name}}. Last time we talked about {{last_topic}}. Would you like to continue from there or explore something new?\"\n- Check their energy: \"How are you feeling today? Are you in the mood to dive deep or keep things lighter?\"\n\n### Transitioning Topics:\n- \"That'\''s a wonderful story. It makes me curious about [related topic]...\"\n- \"You'\''ve shared so much about [topic]. Shall we explore another chapter of your life?\"\n\n### Closing a Session:\n- Summarize key stories shared\n- Express gratitude: \"Thank you for sharing these precious memories with me.\"\n- Preview next session: \"Next time, we might explore [suggested topic].\"\n- Affirm: \"Your stories matter. I'\''m honored to help preserve them.\"\n\n## Tone Guidelines:\n- **Warm**: Like talking to a trusted friend\n- **Unhurried**: Never rush; let silences happen\n- **Curious**: Genuinely interested in every detail\n- **Affirming**: Validate their experiences and emotions\n- **Gentle**: Especially when touching difficult subjects\n- **Respectful**: Honor their perspective, even if different from your own\n\n## Important Rules:\n- Never judge their choices or opinions\n- Don'\''t correct their memory of events\n- Avoid leading questions that suggest \"right\" answers\n- Let them be the expert on their own life\n- Be patient with tangents - they often lead to treasures\n- Remember details they share and reference them later",
        "llm": "gpt-4o",
        "temperature": 0.8,
        "max_tokens": 1500,
        "tools": [
          {
            "type": "webhook",
            "name": "save_story",
            "description": "Save a completed story or memory to the memoir collection",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/memoir/save-story",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "user_id": {"type": "string"},
                  "chapter": {"type": "string", "description": "Life chapter: origins, coming_of_age, relationships, work, family, wisdom"},
                  "title": {"type": "string", "description": "Brief title for the story"},
                  "summary": {"type": "string", "description": "Summary of the story shared"},
                  "key_people": {"type": "array", "description": "Names of people mentioned"},
                  "time_period": {"type": "string", "description": "When this story took place"},
                  "themes": {"type": "array", "description": "Themes identified: love, loss, triumph, growth, etc."},
                  "emotional_tone": {"type": "string", "description": "Overall emotional quality: joyful, bittersweet, reflective, etc."}
                },
                "required": ["user_id", "chapter", "summary"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "get_previous_sessions",
            "description": "Retrieve summaries from previous memoir sessions",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/memoir/sessions",
              "method": "GET",
              "query_params_schema": {
                "properties": {
                  "user_id": {"type": "string"},
                  "limit": {"type": "integer", "description": "Number of recent sessions to retrieve"}
                },
                "required": ["user_id"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "get_chapter_progress",
            "description": "Check which life chapters have been explored",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/memoir/progress",
              "method": "GET",
              "query_params_schema": {
                "properties": {
                  "user_id": {"type": "string"}
                },
                "required": ["user_id"]
              }
            }
          },
          {
            "type": "webhook",
            "name": "add_person",
            "description": "Record a person mentioned in the memoir with their relationship",
            "api_schema": {
              "url": "https://your-webhook-url.com/api/memoir/people",
              "method": "POST",
              "request_body_schema": {
                "type": "object",
                "properties": {
                  "user_id": {"type": "string"},
                  "name": {"type": "string", "description": "Person'\''s name"},
                  "relationship": {"type": "string", "description": "How they'\''re related to the speaker"},
                  "significance": {"type": "string", "description": "Brief note on why they'\''re important"},
                  "time_period": {"type": "string", "description": "When this person was significant"}
                },
                "required": ["user_id", "name", "relationship"]
              }
            }
          },
          {
            "type": "system",
            "name": "end_call",
            "description": "End the session when the speaker wishes to stop"
          }
        ]
      },
      "dynamic_variables": {
        "dynamic_variable_placeholders": {
          "user_name": "there",
          "last_topic": "your early years",
          "sessions_completed": "0",
          "stories_collected": "0"
        }
      }
    },
    "asr": {
      "provider": "elevenlabs",
      "quality": "high"
    },
    "tts": {
      "model_id": "eleven_turbo_v2_5",
      "voice_id": "21m00Tcm4TlvDq8ikWAM",
      "stability": 0.7,
      "similarity_boost": 0.85,
      "optimize_streaming_latency": "1"
    },
    "turn": {
      "turn_timeout": 30.0,
      "silence_end_call_timeout": 60.0,
      "turn_eagerness": "patient",
      "soft_timeout_config": {
        "timeout_seconds": 45,
        "message": "Take your time. I'\''m here whenever you'\''re ready to continue."
      }
    },
    "conversation": {
      "max_duration_seconds": 3600
    }
  },
  "platform_settings": {
    "evaluation": {
      "criteria": [
        {
          "id": "story_captured",
          "name": "Story Captured",
          "type": "prompt",
          "conversation_goal_prompt": "Determine if at least one meaningful story or memory was shared and captured"
        },
        {
          "id": "emotional_safety",
          "name": "Emotional Safety",
          "type": "prompt",
          "conversation_goal_prompt": "Assess if the speaker appeared comfortable and the interviewer handled sensitive topics appropriately"
        },
        {
          "id": "depth_achieved",
          "name": "Depth Achieved",
          "type": "prompt",
          "conversation_goal_prompt": "Evaluate if the conversation went beyond surface-level facts to explore emotions, significance, and meaning"
        }
      ]
    },
    "data_collection": {
      "chapters_discussed": {
        "type": "array",
        "description": "Which life chapters were touched on in this session"
      },
      "stories_shared": {
        "type": "integer",
        "description": "Number of distinct stories or memories shared"
      },
      "people_mentioned": {
        "type": "array",
        "description": "Names and relationships of people mentioned"
      },
      "emotional_moments": {
        "type": "string",
        "description": "Note any particularly emotional or significant moments"
      },
      "session_quality": {
        "type": "string",
        "description": "Overall assessment: rich, moderate, surface-level"
      },
      "suggested_next_topic": {
        "type": "string",
        "description": "Recommended topic for next session"
      }
    },
    "privacy": {
      "record_voice": true,
      "retention_days": 365
    }
  }
}'
```

---

## OpenMemory Integration

All agents can be enhanced with persistent memory using OpenMemory. This enables:

- **Caller Recognition**: Personalized greetings based on history
- **Conversation Continuity**: Pick up where you left off
- **Preference Learning**: Remember user preferences across calls
- **Behavioral Patterns**: Adapt to individual communication styles

### Configure Webhooks for Memory

Add these webhook URLs to your agent's platform settings to enable OpenMemory integration:

```json
{
  "platform_settings": {
    "workspace_overrides": {
      "conversation_initiation_client_data_webhook": {
        "url": "https://your-server.com/webhook/client-data",
        "request_headers": {
          "Authorization": "Bearer YOUR_WEBHOOK_SECRET"
        }
      },
      "webhooks": {
        "events": ["transcript"],
        "send_audio": false
      }
    },
    "overrides": {
      "enable_conversation_initiation_client_data_from_webhook": true
    }
  }
}
```

### Memory Flow

```
1. Call Starts
   └─→ Client-Data Webhook called
       └─→ Query OpenMemory for caller profile
           └─→ Return dynamic_variables + first_message override

2. Call In Progress
   └─→ Agent uses dynamic variables in conversation
   └─→ Search-Data Webhook for mid-call memory queries

3. Call Ends
   └─→ Post-Call Webhook receives transcript
       └─→ Extract memories from conversation
           └─→ Store in OpenMemory for future calls
```

### Example Client-Data Response

```json
{
  "dynamic_variables": {
    "user_name": "Sarah",
    "user_profile_summary": "Returning customer, prefers email follow-ups",
    "last_call_summary": "Discussed billing inquiry on Dec 1"
  },
  "conversation_config_override": {
    "agent": {
      "first_message": "Welcome back, Sarah! I see we spoke recently about your billing. How can I help you today?"
    }
  }
}
```

---

## Webhook Configuration

### Setting Up Post-Call Webhooks

1. **Create webhook URL endpoint** on your server
2. **Configure in ElevenLabs Dashboard**:
   - Go to Agent Settings → Webhooks
   - Add Post-Call Webhook URL
   - Copy HMAC Secret for signature validation

### HMAC Signature Validation

```python
import hmac
import hashlib
import time

def verify_elevenlabs_webhook(signature_header: str, body: bytes, secret: str) -> bool:
    """Verify ElevenLabs webhook signature."""
    try:
        parts = dict(part.split("=") for part in signature_header.split(","))
        timestamp = parts.get("t", "")
        provided_hash = parts.get("v0", "")

        # Check timestamp (30-minute tolerance)
        if abs(time.time() - int(timestamp)) > 1800:
            return False

        # Compute expected signature
        message = f"{timestamp}.{body.decode()}"
        expected_hash = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(provided_hash, expected_hash)
    except Exception:
        return False
```

---

## Best Practices

### System Prompt Design

1. **Be Specific**: Clear role definition and boundaries
2. **Include Examples**: Show expected dialogue patterns
3. **Define Escalation**: When and how to transfer to humans
4. **Set Tone**: Explicit guidance on personality and style

### Voice Selection

| Use Case | Voice Characteristics | Recommended Settings |
|----------|----------------------|---------------------|
| Customer Support | Clear, patient | Stability: 0.6, Similarity: 0.8 |
| Sales | Energetic, warm | Stability: 0.5, Similarity: 0.75 |
| Healthcare | Calm, reassuring | Stability: 0.65, Similarity: 0.8 |
| Financial | Professional, trustworthy | Stability: 0.7, Similarity: 0.8 |
| Hospitality | Elegant, warm | Stability: 0.6, Similarity: 0.8 |
| Memoir | Gentle, unhurried | Stability: 0.7, Similarity: 0.85 |

### Turn Configuration

| Scenario | Turn Timeout | Silence End Call | Eagerness |
|----------|-------------|------------------|-----------|
| Quick inquiries | 8-10s | 20s | normal |
| Complex support | 15s | 45s | patient |
| Elderly callers | 20-30s | 60s | patient |
| Sales calls | 10-12s | 20s | normal |
| Emotional conversations | 30s | 60s | patient |

### LLM Selection

| Complexity | Recommended LLM | Temperature |
|------------|-----------------|-------------|
| Simple FAQ | gpt-4o-mini | 0.3-0.5 |
| General support | gpt-4o-mini | 0.5-0.7 |
| Complex reasoning | gpt-4o | 0.5-0.7 |
| Creative/empathetic | gpt-4o or claude-3-5-sonnet | 0.7-0.9 |
| Tool-heavy | gpt-4o or claude-3-5-sonnet | 0.4-0.6 |

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Agent not responding | Invalid API key | Verify `ELEVENLABS_API_KEY` is correct |
| No voice output | Invalid voice_id | Check voice exists in your account |
| Webhook not called | URL not accessible | Ensure HTTPS and public accessibility |
| HMAC validation fails | Wrong secret | Re-copy secret from ElevenLabs dashboard |
| Agent cuts off early | Short timeout | Increase `silence_end_call_timeout` |
| Poor transcription | Low audio quality | Use higher quality ASR setting |

### Debug Commands

```bash
# Test API key
curl -X GET "https://api.elevenlabs.io/v1/user" \
  -H "xi-api-key: $ELEVENLABS_API_KEY"

# List your agents
curl -X GET "https://api.elevenlabs.io/v1/convai/agents" \
  -H "xi-api-key: $ELEVENLABS_API_KEY"

# Get specific agent
curl -X GET "https://api.elevenlabs.io/v1/convai/agents/{agent_id}" \
  -H "xi-api-key: $ELEVENLABS_API_KEY"

# List available voices
curl -X GET "https://api.elevenlabs.io/v1/voices" \
  -H "xi-api-key: $ELEVENLABS_API_KEY"
```

---

## Additional Resources

- [ElevenLabs Documentation](https://elevenlabs.io/docs)
- [Agents Platform Overview](https://elevenlabs.io/docs/agents-platform)
- [Voice Library](https://elevenlabs.io/app/voice-library)
- [API Reference](https://elevenlabs.io/docs/api-reference)
- [OpenMemory Integration Guide](../README.md)

---

## Support

- **ElevenLabs Support**: [support@elevenlabs.io](mailto:support@elevenlabs.io)
- **API Status**: [status.elevenlabs.io](https://status.elevenlabs.io)
- **Community**: [Discord](https://discord.gg/elevenlabs)