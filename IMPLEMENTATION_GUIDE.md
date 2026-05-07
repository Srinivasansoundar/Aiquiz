# Performance-Based Difficulty Auto-Adjustment - Implementation Guide

## 📋 Overview
Instead of advancing difficulty only after 2 consecutive correct answers, this feature will:
- Track the last **5 questions** performance
- **Auto-advance** to harder difficulty if 100% correct on recent 5 questions
- **Auto-regress** to easier difficulty if success rate < 40% on recent 5 questions
- Skip levels for faster progression when user shows mastery

---

## 🔧 Step-by-Step Implementation

### **STEP 1: Update QuizState TypedDict**
**File:** `backend/src/control/agents/graph.py`

**What to add:** Add these fields to the `QuizState` TypedDict (around line 19-40):

```python
class QuizState(TypedDict):
    # ... existing fields ...
    
    # NEW: Track recent performance for auto-adjustment
    recent_performance: List[bool]  # List of last 5 question results (True=correct, False=wrong)
    performance_check_count: int    # Count of questions since last auto-adjustment check
```

**Why:**
- `recent_performance`: Stores whether user answered last 5 questions correctly
- `performance_check_count`: Counter to know when to evaluate performance (every 5 questions)

---

### **STEP 2: Initialize These Fields in start_session_node**
**File:** `backend/src/control/agents/graph.py`

**Location:** Inside the `start_session_node()` function, add to the return dictionary (around line 78):

```python
def start_session_node(state: QuizState) -> QuizState:
    return {
        # ... existing fields ...
        
        # NEW: Initialize performance tracking
        "recent_performance": [],              # Start with empty list
        "performance_check_count": 0,          # Start with 0
    }
```

**Why:** Every new session needs these counters initialized to track performance.

---

### **STEP 3: Create New Function for Auto-Adjustment Logic**
**File:** `backend/src/control/agents/graph.py`

**Where to add:** Add this function BEFORE the `create_quiz_graph()` function (around line 560):

```python
def auto_adjust_difficulty_based_on_performance(state: QuizState) -> QuizState:
    """
    Automatically adjust difficulty based on recent performance.
    
    Rules:
    - If 100% correct on last 5 questions → advance difficulty (skip levels if needed)
    - If < 40% correct on last 5 questions → regress difficulty (go down one level)
    - Otherwise → keep current difficulty
    
    Returns:
        Updated state with new difficulty level
    """
    
    recent = state.get("recent_performance", [])
    
    # Only check if we have at least 5 recent questions
    if len(recent) >= 5:
        # Get the last 5 results
        last_five = recent[-5:]
        success_count = sum(last_five)  # Count True values (correct answers)
        success_rate = success_count / 5  # Calculate percentage
        
        current_difficulty = state.get("current_difficulty", "easy")
        difficulty_levels = ["easy", "medium", "hard"]
        current_index = difficulty_levels.index(current_difficulty)
        
        print(f"📊 Performance Check: {success_count}/5 correct ({success_rate*100:.0f}%)")
        
        # 100% Success - Advance to harder difficulty
        if success_rate == 1.0:  # 5/5 correct
            if current_index < len(difficulty_levels) - 1:
                # Can advance one level
                state["current_difficulty"] = difficulty_levels[current_index + 1]
                state["correct_count_at_difficulty"] = 0
                print(f"✅ ADVANCING to {state['current_difficulty']} (100% performance!)")
            
            # Reset recent performance after checking
            state["recent_performance"] = []
        
        # Poor Performance - Regress to easier difficulty
        elif success_rate < 0.4:  # Less than 40% correct
            if current_index > 0:
                # Go back one level
                state["current_difficulty"] = difficulty_levels[current_index - 1]
                state["correct_count_at_difficulty"] = 0
                print(f"❌ REGRESSING to {state['current_difficulty']} (poor performance)")
            
            # Reset recent performance after checking
            state["recent_performance"] = []
    
    return state
```

**Why:** This function contains the core logic for auto-adjusting difficulty based on performance metrics.

---

### **STEP 4: Update record_answer_to_history Function**
**File:** `backend/src/control/agents/graph.py`

**Location:** Inside `record_answer_to_history()` function (around line 501):

**What to do:** Add this code at the END of the function, just before `return state`:

```python
def record_answer_to_history(state: QuizState) -> QuizState:
    """Record the current question and answer to the quiz history..."""
    
    # ... existing code ...
    
    state["quiz_history"] = quiz_history
    state["question_count"] = state.get("question_count", 0) + 1
    
    if not state.get("is_correct", False):
        state["hint_attempt"] = 0
    state["wrong_on_first_try_for_current_question"] = False
    
    # NEW: Track recent performance for auto-adjustment
    recent_perf = state.get("recent_performance", [])
    is_correct = state.get("is_correct", False)
    recent_perf.append(is_correct)  # Add True if correct, False if wrong
    state["recent_performance"] = recent_perf
    
    return state
```

**Why:** Every time a question is recorded, we save whether it was answered correctly for performance tracking.

---

### **STEP 5: Update route_based_answer Function**
**File:** `backend/src/control/agents/graph.py`

**Location:** Modify the `route_based_answer()` function (around line 320):

**Current Code:**
```python
def route_based_answer(state: QuizState) -> str:
    """Route to next node based on whether answer is correct and attempt count."""
    
    is_correct = state.get("is_correct", False)
    hint_attempt = state.get("hint_attempt", 0)
    
    if is_correct:
        return "record_answer_to_history"
    else:
        if hint_attempt < 3:
            return "generate_hint_node"
        else:
            return "record_answer_to_history"
```

**What to change:** Replace the `if is_correct:` block:

```python
def route_based_answer(state: QuizState) -> str:
    """Route to next node based on whether answer is correct and attempt count."""
    
    is_correct = state.get("is_correct", False)
    hint_attempt = state.get("hint_attempt", 0)
    
    if is_correct:
        # NEW: After recording, check if we should auto-adjust difficulty
        state["should_check_performance"] = True
        return "record_answer_to_history"
    else:
        if hint_attempt < 3:
            return "generate_hint_node"
        else:
            return "record_answer_to_history"
```

**Why:** We add a flag to indicate performance check is needed after recording.

---

### **STEP 6: Update route_after_recording Function**
**File:** `backend/src/control/agents/graph.py`

**Location:** Modify the `route_after_recording()` function (around line 598):

**Current Code:**
```python
def route_after_recording(state: QuizState) -> str:
        if state.get("is_correct", False):
            return "check_difficulty_progression"
        else:
            return "load_next_chunk"
```

**What to change:** Replace with:

```python
def route_after_recording(state: QuizState) -> str:
    """Route after recording to check performance or progression."""
    
    if state.get("is_correct", False):
        # First check auto-adjustment based on recent performance
        recent_perf = state.get("recent_performance", [])
        if len(recent_perf) >= 5:
            # Auto-adjust if we have 5+ recent questions
            state = auto_adjust_difficulty_based_on_performance(state)
            return "load_next_chunk"
        else:
            # Otherwise, use original difficulty progression logic
            return "check_difficulty_progression"
    else:
        return "load_next_chunk"
```

**Why:** This routes to auto-adjustment when performance data is available, otherwise uses the original progression logic.

---

### **STEP 7: Update create_quiz_graph Function**
**File:** `backend/src/control/agents/graph.py`

**Location:** Inside `create_quiz_graph()` function, ensure the node is added (around line 620):

**Check:** Make sure this line exists in the graph creation:
```python
graph.add_node("check_difficulty_progression", check_difficulty_progression)
```

**If not already there, add it near line 625.**

---

## 📊 Summary of Changes

| File | Function | Change Type | What to Add/Modify |
|------|----------|-------------|-------------------|
| graph.py | QuizState | Add Fields | `recent_performance`, `performance_check_count` |
| graph.py | start_session_node() | Add Init | Initialize new fields to `[]` and `0` |
| graph.py | NEW | Create Function | `auto_adjust_difficulty_based_on_performance()` |
| graph.py | record_answer_to_history() | Add Code | Track is_correct in `recent_performance` list |
| graph.py | route_based_answer() | Modify | Add flag for performance check |
| graph.py | route_after_recording() | Modify | Call auto-adjust when 5+ questions tracked |
| graph.py | create_quiz_graph() | Verify | Ensure node is included in graph |

---

## 🎯 How It Works (Flow)

```
User answers Question 1 → Correct ✅
  └─ recent_performance = [True]

User answers Question 2 → Wrong ❌
  └─ recent_performance = [True, False]

User answers Question 3 → Correct ✅
  └─ recent_performance = [True, False, True]

User answers Question 4 → Correct ✅
  └─ recent_performance = [True, False, True, True]

User answers Question 5 → Correct ✅
  └─ recent_performance = [True, False, True, True, True]
  └─ Success Rate = 4/5 = 80%
  └─ No auto-adjustment (need 100% or <40%)
  └─ recent_performance resets to []

User answers Question 6 → Correct ✅
  └─ recent_performance = [True]

User answers Question 7 → Correct ✅
  └─ recent_performance = [True, True]

User answers Question 8 → Correct ✅
  └─ recent_performance = [True, True, True]

User answers Question 9 → Correct ✅
  └─ recent_performance = [True, True, True, True]

User answers Question 10 → Correct ✅
  └─ recent_performance = [True, True, True, True, True]
  └─ Success Rate = 5/5 = 100% 🎉
  └─ AUTO-ADVANCE: easy → medium ⬆️
  └─ recent_performance resets to []
```

---

## 🧪 Testing Checklist

After implementation, test these scenarios:

- [ ] User gets all 5 recent questions correct → Difficulty advances ✅
- [ ] User gets less than 40% on recent 5 → Difficulty regresses ❌
- [ ] User gets 60-90% on recent 5 → Difficulty stays same ⏸️
- [ ] Counter resets after auto-adjustment happens
- [ ] New session starts with empty performance list
- [ ] Original 2-consecutive-correct progression still works if <5 questions answered

---

## 📝 Optional Enhancements

After implementing the basic version, you could also add:

### **Enhancement 1: Show Performance on Frontend**
Modify `await_user_answer()` in graph.py to return:
```python
interrupt_data = {
    "question": question_data.get("question", ""),
    "options": question_data.get("options", []),
    "recent_performance": state.get("recent_performance", []),  # NEW
    "recent_score": f"{sum(state.get('recent_performance', []))} / {len(state.get('recent_performance', []))}",  # NEW
    # ... other fields ...
}
```

### **Enhancement 2: Configurable Thresholds**
Add to QuizState:
```python
advance_threshold: float  # Default 1.0 (100%)
regress_threshold: float  # Default 0.4 (40%)
```

---

## ✅ Expected Outcome

After implementation, your quiz will:
1. **Smarter progression** - Users who master a level advance faster
2. **Adaptive challenge** - Users who struggle regress to easier levels
3. **Better UX** - Questions feel appropriately challenging
4. **Data tracking** - Recent performance is visible in metrics

---

## 🚀 Next Steps

1. Make all 7 changes listed above
2. Test with a quiz session
3. Monitor console logs for "ADVANCING" / "REGRESSING" messages
4. Verify in frontend that difficulty updates correctly
5. Add optional enhancements if desired

**That's it!** This gives you true adaptive learning without changing the core architecture. 🎓
