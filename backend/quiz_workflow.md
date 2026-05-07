# Quiz Workflow Diagram

```mermaid
graph TD
    START([Start]) --> start_session["🎯 start_session<br/>Initialize Quiz State"]
    start_session --> load_chunk1["📚 load_next_chunk<br/>Fetch Content Chunk"]
    
    load_chunk1 --> check_chunks{Chunks<br/>Available?}
    check_chunks -->|Yes| generate_q["❓ generate_question<br/>Create Question<br/>with Difficulty Level"]
    check_chunks -->|No| end_session["✅ end_session<br/>Quiz Completed"]
    
    generate_q --> await_answer["⏸️ await_user_answer<br/>Wait for User Input"]
    await_answer --> evaluate["🔍 evaluator_answer<br/>Check if Correct"]
    
    evaluate --> route{Answer<br/>Correct?}
    route -->|Yes| check_prog["📈 check_difficulty_progression<br/>Track Correct Count<br/>Advance if 2+ Correct"]
    route -->|No & Attempts < 3| generate_hint["💡 generate_hint<br/>Attempt: 1/2/3<br/>Generate/Show Answer"]
    route -->|No & Attempts >= 3| load_chunk2["📚 load_next_chunk"]
    
    generate_hint --> await_answer
    check_prog --> load_chunk2
    load_chunk2 --> check_chunks
    
    end_session --> END([End])
    
    style START fill:#90EE90
    style END fill:#FFB6C6
    style start_session fill:#87CEEB
    style load_chunk1 fill:#87CEEB
    style load_chunk2 fill:#87CEEB
    style generate_q fill:#FFD700
    style await_answer fill:#FFA500
    style evaluate fill:#FFA500
    style check_prog fill:#DDA0DD
    style generate_hint fill:#98FB98
    style end_session fill:#FFB6C6
    style check_chunks fill:#FFF8DC
    style route fill:#FFF8DC
```

## Node Descriptions

| Node | Purpose | Transitions |
|------|---------|-------------|
| **start_session** | Initialize quiz state, set difficulty to "easy" | → load_next_chunk |
| **load_next_chunk** | Fetch next content chunk from ChromaDB or topic_chunks | → check_chunks_available |
| **generate_question** | Create multiple-choice question based on difficulty level | → await_user_answer |
| **await_user_answer** | Pause execution and wait for user answer (interrupt) | → evaluator_answer |
| **evaluator_answer** | Compare user answer with correct answer | → route_based_answer |
| **check_difficulty_progression** | Increment correct count; advance difficulty after 2 consecutive correct | → load_next_chunk |
| **generate_hint** | Generate hints (attempt 1-2) or show correct answer (attempt 3) | → await_user_answer |
| **end_session** | Complete quiz when no more chunks available | → END |

## Difficulty Progression

```
🟢 Easy (Recall) 
    ↓ (2 consecutive correct)
🟡 Medium (Understanding)
    ↓ (2 consecutive correct)
🔴 Hard (Synthesis)
```

## Decision Points

### check_chunks_available
- **Yes** → Generate next question
- **No** → End quiz session

### route_based_answer
- **Correct** → Check difficulty progression
- **Wrong (attempts < 3)** → Generate hint
- **Wrong (attempts ≥ 3)** → Load next chunk
