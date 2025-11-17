# AI Video Editing Tool - Documentation Package
## Extracted from "Grammar of the Edit" by Roy Thompson & Christopher J. Bowen

## Overview
This package contains AI prompts and reference materials for building an intelligent video editing assistant based on established editorial grammar and best practices.

---

## Files Included

### 1. **ai_video_editing_assistant_prompt.md**
**Purpose**: Comprehensive system prompt for AI editing tool  
**Use Case**: Full implementation of AI video editing assistant  
**Length**: ~500 lines  
**Contains**:
- Complete shot type taxonomy
- 6-element edit analysis framework
- All transition types with detailed usage guidelines
- Edit category classifications
- General editing practices
- News-specific guidelines
- Common issues to avoid
- Decision-making framework

**Best For**: 
- Training AI models
- Comprehensive reference documentation
- Understanding full editorial grammar

---

### 2. **ai_editor_condensed_prompt.md**
**Purpose**: Practical system prompt for implementation  
**Use Case**: Actual AI tool deployment  
**Length**: ~100 lines  
**Contains**:
- Streamlined analysis framework
- Core 6-element evaluation system
- Critical rules (always/never)
- Output structure template
- Scoring system for edit quality

**Best For**:
- LLM system prompts
- Token-efficient implementation
- Quick AI integration

---

### 3. **editing_quick_reference.md**
**Purpose**: Human editor reference guide  
**Use Case**: Printable cheat sheet, training material  
**Length**: ~200 lines  
**Contains**:
- Shot type quick lookup
- 6-element checklist
- 180-degree rule diagram
- Decision tree
- Common mistakes list
- Golden rules summary

**Best For**:
- Training human editors
- Quick consultation during edits
- Teaching material
- Desk reference

---

### 4. **ai_editor_sample_analysis.md**
**Purpose**: Working example of AI analysis  
**Use Case**: Template for output format  
**Length**: ~400 lines  
**Contains**:
- Complete story analysis walkthrough
- Shot-by-shot evaluation with 6-element checks
- Edit point recommendations with rationale
- Alternative edit options
- Audio treatment suggestions
- Continuity checks
- Final statistics

**Best For**:
- Understanding output format
- Testing AI tool accuracy
- Training examples
- Client demonstrations

---

## Implementation Recommendations

### For Building an AI Editing Tool:

**PHASE 1: Core Prompt**
- Start with `ai_editor_condensed_prompt.md`
- Implement 6-element evaluation system
- Focus on cut recommendations first

**PHASE 2: Shot Analysis**  
- Add shot type classification from comprehensive prompt
- Implement quality assessment
- Build duration recommendations

**PHASE 3: Advanced Features**
- Add transition type selection (dissolve, wipe, fade)
- Implement split edit suggestions
- Add alternative edit paths

**PHASE 4: Output Refinement**
- Use `ai_editor_sample_analysis.md` as template
- Structure consistent JSON/XML output
- Add visualization of edit timeline

---

## Key Concepts from "Grammar of the Edit"

### The 6-Element Framework (CORE INNOVATION)
Every edit decision evaluated on:
1. Information (new data?)
2. Motivation (why now?)
3. Composition (visual difference?)
4. Camera Angle (perspective change?)
5. Continuity (consistency maintained?)
6. Sound (audio supports?)

**Scoring**: 4-6 elements = Strong | 2-3 = Weak | 0-1 = Avoid

### Shot Type Classification
11 standard types from XCU to XLS provide:
- Common vocabulary for analysis
- Predictable information content
- Duration guidance
- Compositional expectations

### Transition Types
4 basic transitions with specific meanings:
- **Cut**: 90% of edits, invisible, continuous action
- **Dissolve**: Time/emotion, visible, 1-10% of edits
- **Wipe**: Graphical, rare in news
- **Fade**: Chapter markers only

### The 180-Degree Rule
Fundamental spatial orientation system:
- Maintains screen direction
- Preserves viewer geography
- Prevents confusing jumps
- Essential for dialogue scenes

### Edit Categories
5 types that can combine:
- Action (cut on movement)
- Screen Position (lead the eye)
- Form (match shapes/sounds)
- Concept (create meaning)
- Combined (multiple types)

---

## Sample Integration Pseudocode

```python
def analyze_edit_point(shot_a, shot_b, cut_time):
    # Evaluate 6 elements
    scores = {
        'information': check_new_information(shot_a, shot_b),
        'motivation': find_motivation(shot_a, cut_time),
        'composition': compare_composition(shot_a, shot_b),
        'camera_angle': measure_angle_change(shot_a, shot_b),
        'continuity': check_continuity(shot_a, shot_b),
        'sound': evaluate_audio_transition(shot_a, shot_b)
    }
    
    # Calculate strength
    passed_elements = sum(1 for v in scores.values() if v > 0.7)
    
    if passed_elements >= 4:
        return "STRONG_EDIT", scores, suggest_cut()
    elif passed_elements >= 2:
        return "WEAK_EDIT", scores, suggest_alternatives()
    else:
        return "AVOID_EDIT", scores, find_better_cut_point()
```

---

## Testing the AI Tool

Use these test scenarios from book:

1. **Action Edit Test**
   - Man picks up book at library
   - Should identify: motivation (action), continuity (movement match)
   - Expected: Strong cut recommendation on book lift

2. **Dialogue Test**  
   - Two-person conversation
   - Should maintain: 180-degree rule, eyelines, screen position
   - Expected: Alternating cuts with matched framing

3. **Time Compression Test**
   - Multiple shots of same subject
   - Should suggest: Dissolves vs. cuts based on time passage
   - Expected: Dissolve recommendations for time jumps

4. **Jump Cut Detection**
   - Similar angles, minimal change
   - Should flag: Insufficient angle change, composition too similar
   - Expected: Avoid recommendation with alternatives

---

## News Editing Specific Notes

When applying to news content:

**ADJUSTMENTS NEEDED**:
- Prioritize factual accuracy over artistic flow
- Cuts dominate (95%+ of transitions)
- Dissolves rare/never
- Respect complete thoughts in sound bites
- Temporal accuracy critical
- Speaker intent preserved

**ADDITIONAL CHECKS**:
- Quote context maintained?
- Time references accurate?
- Attribution clear?
- B-roll supports claims?

---

## Extension Opportunities

### Beyond the Book:

1. **Multi-camera Editing**
   - Adapt principles for live switching
   - Real-time angle selection

2. **Modern Formats**
   - Vertical video (9:16) adaptations
   - Social media duration constraints
   - Platform-specific styles

3. **Automated Systems**
   - AI shot classification
   - Automatic rough cuts
   - Quality scoring

4. **Collaborative Features**
   - Edit decision lists (EDL)
   - Version comparison
   - Comment/approval workflow

---

## Credits and Sources

**Original Source**: 
"Grammar of the Edit, Second Edition"  
Roy Thompson & Christopher J. Bowen  
Focal Press, 2009

**Core Principles**:
- 100+ years of film editing evolution
- Established visual grammar
- Industry-standard practices
- Professional workflow guidance

**Application Domain**:
- Film and television
- News broadcasting
- Documentary production
- Commercial content
- Digital media

---

## Next Steps for Implementation

1. **Choose your foundation**: Use condensed prompt for deployment
2. **Test with sample**: Run through sample analysis format
3. **Iterate output structure**: Match to your workflow needs
4. **Add domain specifics**: Enhance for news/sports/documentary
5. **Build validation**: Test against human editor decisions
6. **Scale gradually**: Start with shot analysis, add edit recommendations
7. **Gather feedback**: Learn from editor corrections

---

## Questions This System Can Answer

✅ "What type of shot is this?"  
✅ "Where should I cut?"  
✅ "Why is this a good/bad edit?"  
✅ "What transition should I use?"  
✅ "How long should this shot be?"  
✅ "Does this edit respect the 180-degree rule?"  
✅ "What are alternative edit points?"  
✅ "Is this a jump cut?"  
✅ "How can I improve this sequence?"  
✅ "What audio treatment do I need?"

---

## Limitations & Considerations

**What the Book Covers**:
- Visual grammar fundamentals
- Edit decision framework
- Transition types
- Continuity systems
- General best practices

**What the Book Doesn't Cover**:
- Specific software workflows
- Color grading decisions  
- Advanced audio mixing
- Effects and graphics
- Modern social media formats
- Live/streaming considerations

**AI Tool Limitations**:
- Cannot assess emotional impact perfectly
- Requires training data for accuracy
- May not capture creative innovations
- Context-dependent decisions need human judgment
- Cultural/genre variations not fully codified

---

## Support & Resources

For questions about implementation:
- Reference comprehensive prompt for detailed explanations
- Use sample analysis as output template
- Consult quick reference for decision flowcharts
- Test edge cases against 6-element framework

**Remember**: "Effective creativity overrules grammar" - The tool should guide, not dictate. Human editors make final creative decisions.

---

## Document Version
Created: November 14, 2025  
Source Material: Grammar of the Edit (2nd Edition)  
Prepared for: Thomson Reuters AI Newsroom Tools  
Format: Markdown documentation package
