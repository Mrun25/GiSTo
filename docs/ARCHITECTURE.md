# GiSTo Architecture

GiSTo is built as a set of decoupled services that communicate through a shared backend API. It consists of a Telegram bot (for the business owner), a React dashboard (for the CA), and a FastAPI backend (to tie everything together with the PostgreSQL database).

## High-Level System Architecture

```mermaid
graph TD
    %% Components
    Owner([Business Owner])
    CA([Chartered Accountant])
    
    Bot[Telegram Bot\n(python-telegram-bot)]
    Dashboard[CA Dashboard\n(React/Vite)]
    
    Backend[FastAPI Backend\n(Core Logic)]
    DB[(PostgreSQL)]
    
    MockGSP[[Mock GSP API]]
    MockExtraction[[Mock LLM Extractor]]
    
    %% Relationships
    Owner -->|Sends Invoices| Bot
    Bot -->|REST API| Backend
    
    CA -->|Views Portfolio| Dashboard
    Dashboard -->|REST API| Backend
    
    Backend <-->|SQLAlchemy| DB
    Backend -->|Validate & Sync| MockGSP
    Backend -->|Extract Data| MockExtraction
```

## Workflows

### 1. Invoice Submission Flow
```mermaid
sequenceDiagram
    participant Owner as Business Owner
    participant Bot as Telegram Bot
    participant API as FastAPI Backend
    participant Extractor as Extraction Service
    
    Owner->>Bot: Uploads Invoice (Image/PDF)
    Bot->>API: Send file for extraction
    API->>Extractor: Process document
    Extractor-->>API: Extracted structured data
    API-->>Bot: Return data with confidence scores
    Bot-->>Owner: Ask to confirm fields (especially low confidence)
    Owner->>Bot: Confirms or corrects fields
    Bot->>API: Save confirmed invoice
    API-->>Bot: Success
    Bot-->>Owner: Invoice saved!
```

### 2. Onboarding & GST Sync Flow
```mermaid
sequenceDiagram
    participant Owner as Business Owner
    participant Bot as Telegram Bot
    participant API as FastAPI Backend
    participant GSP as GST Suvidha Provider
    
    Owner->>Bot: /start
    Bot-->>Owner: Asks for GSTIN
    Owner->>Bot: Provides GSTIN
    Bot->>API: Validate GSTIN
    API->>GSP: Check GSTIN status
    GSP-->>API: Returns Legal Name & Status
    API-->>Bot: Validation response
    Bot-->>Owner: Please confirm your business name
    Owner->>Bot: Confirms
    Bot->>API: Create Business profile & request OTP link
    API-->>Bot: Returns secure OTP link
    Bot-->>Owner: Send link for GSP authorization
    Owner->>Bot: Completes OTP & sends reference
    Bot->>API: Complete authorization
    API-->>Bot: Success
```
