# Video Processing Demo - Specification Document

## 1. Project Overview

**Project Name:** RenditionDemo  
**Project Type:** Web Application (Python Streamlit)  
**Core Functionality:** A video processing demo that uses AI to extract prompts from video content and regenerate new videos based on modified prompts  
**Target Users:** Content creators, video editors, AI enthusiasts

---

## 2. UI/UX Specification

### 2.1 Layout Structure

**Multi-page Application:**
- Sidebar navigation with 4 main pages
- Clean, professional interface with consistent styling

**Page Structure:**
- Header with task info display
- Main content area with responsive layout
- Consistent padding and spacing

### 2.2 Visual Design

**Color Palette:**
- Primary: `#6366F1` (Indigo)
- Secondary: `#8B5CF6` (Violet)
- Background: `#0F172A` (Dark slate)
- Surface: `#1E293B` (Slate 800)
- Text Primary: `#F8FAFC` (Slate 50)
- Text Secondary: `#94A3B8` (Slate 400)
- Success: `#22C55E` (Green)
- Warning: `#F59E0B` (Amber)
- Error: `#EF4444` (Red)
- Border: `#334155` (Slate 700)

**Typography:**
- Font Family: System font (sans-serif)
- Heading sizes: H1: 2rem, H2: 1.5rem, H3: 1.25rem
- Body text: 1rem
- Small text: 0.875rem

**Spacing System:**
- Base unit: 0.5rem (8px)
- Margins: 1rem, 1.5rem, 2rem
- Card padding: 1rem
- Gap between elements: 0.5rem, 1rem

**Visual Effects:**
- Card shadows: subtle dark shadows
- Border radius: 0.5rem for cards, 0.25rem for buttons
- Hover effects on interactive elements
- Smooth transitions (0.2s)

### 2.3 Components

**Page 1 - Video Upload:**
- File uploader component (accepts mp4, avi, mov)
- Video preview player
- "Next Step" button (primary style)
- Task ID display
- Processing status indicator

**Page 2 - Character Keyframes:**
- Grid layout for keyframe display
- Image cards with keyframe thumbnails
- Editable text areas for character prompts
- Auto-save on edit
- Character index labels

**Page 3 - Scene Prompts:**
- List/grid layout for scene prompts
- Editable text areas
- Scene index/time labels
- Auto-save functionality

**Page 4 - Generated Video:**
- Video player for generated video
- Generation status indicator
- Regenerate button
- Download option placeholder

**Sidebar:**
- Page navigation
- Current task info
- New task button
- Load existing task option

---

## 3. Functionality Specification

### 3.1 Core Features

**Task Management:**
1. Create new task with unique ID
2. Save all task data to disk (JSON + media files)
3. Load existing task from disk
4. Auto-save on changes

**Video Processing (Page 1):**
1. Upload video file
2. Display video preview
3. Trigger AI analysis (placeholder)
4. Extract character keyframes
5. Extract scene/shot prompts
6. Store results in task data

**Character Analysis (Page 2):**
1. Display all character keyframes
2. Show extracted character prompts
3. Allow prompt editing
4. Auto-save edits

**Scene Analysis (Page 3):**
1. Display all scene shots
2. Show extracted scene prompts
3. Allow prompt editing
4. Auto-save edits

**Video Generation (Page 4):**
1. Combine prompts to generate new video
2. Display generated video
3. Provide regeneration option

### 3.2 User Interactions

- File drag-and-drop for upload
- Click to navigate between pages
- Text editing in prompt fields
- Button clicks for actions
- Page state persistence

### 3.3 Data Handling

**Task Data Structure:**
```json
{
  "task_id": "uuid",
  "created_at": "timestamp",
  "updated_at": "timestamp",
  "status": "enum",
  "source_video": {
    "path": "relative/path.mp4",
    "duration": float,
    "width": int,
    "height": int
  },
  "character_keyframes": [
    {
      "id": "uuid",
      "frame_index": int,
      "timestamp": float,
      "image_path": "relative/path.jpg",
      "prompt": "string",
      "character_description": "string"
    }
  ],
  "scene_prompts": [
    {
      "id": "uuid",
      "start_time": float,
      "end_time": float,
      "prompt": "string",
      "scene_type": "string"
    }
  ],
  "generated_video": {
    "path": "relative/path.mp4",
    "used_character_prompts": ["uuid"],
    "used_scene_prompts": ["uuid"],
    "generated_at": "timestamp"
  }
}
```

**File Storage Structure:**
```
tasks/
  └── {task_id}/
      ├── task.json
      ├── source/
      │   └── video.mp4
      ├── keyframes/
      │   ├── character_001.jpg
      │   └── character_002.jpg
      └── output/
          └── generated.mp4
```

### 3.4 Edge Cases

- Handle empty/no video uploaded state
- Handle large video files (show progress)
- Handle invalid video formats
- Handle AI API errors (placeholder)
- Handle missing task data on load
- Handle concurrent edits

---

## 4. Technical Architecture

### 4.1 File Structure

```
renditionDemo/
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
├── SPEC.md                # This specification
├── pages/
│   ├── 1_📹_视频上传.py       # Page 1: Video upload
│   ├── 2_👤_人物分析.py        # Page 2: Character analysis
│   ├── 3_🎬_镜头分析.py        # Page 3: Scene/shot analysis
│   └── 4_✨_视频生成.py        # Page 4: Video generation
├── modules/
│   ├── __init__.py
│   ├── data_models.py      # Data classes
│   ├── task_manager.py     # Task persistence
│   ├── ai_interface.py     # AI API placeholder
│   └── config.py           # Configuration
└── tasks/                  # Task data storage
```

### 4.2 Dependencies

- streamlit >= 1.28.0
- opencv-python >= 4.8.0
- Pillow >= 10.0.0
- numpy >= 1.24.0

---

## 5. AI Interface Placeholders

### 5.1 Video Analysis API
```python
def analyze_video(video_path: str) -> AnalysisResult:
    """Placeholder for video analysis AI"""
    pass
```

### 5.2 Prompt Generation API
```python
def extract_character_prompts(frames: List[str]) -> List[CharacterPrompt]:
    """Placeholder for character prompt extraction"""
    pass

def extract_scene_prompts(video_path: str) -> List[ScenePrompt]:
    """Placeholder for scene prompt extraction"""
    pass
```

### 5.3 Video Generation API
```python
def generate_video(character_prompts: List, scene_prompts: List) -> str:
    """Placeholder for video generation"""
    pass
```

---

## 6. Acceptance Criteria

### Page 1 - Video Upload
- [ ] User can upload video file (mp4, avi, mov)
- [ ] Uploaded video is displayed in player
- [ ] "Next Step" button triggers AI analysis
- [ ] Processing status is shown
- [ ] Task is saved after upload

### Page 2 - Character Analysis
- [ ] Displays all character keyframes
- [ ] Shows extracted prompts for each keyframe
- [ ] Prompts are editable via text areas
- [ ] Edits are auto-saved
- [ ] Grid layout with proper spacing

### Page 3 - Scene Analysis
- [ ] Displays all scene prompts
- [ ] Shows time ranges for each scene
- [ ] Prompts are editable
- [ ] Edits are auto-saved

### Page 4 - Video Generation
- [ ] Displays generated video if available
- [ ] Shows generation status
- [ ] Regenerate button works
- [ ] Uses modified prompts from pages 2&3

### General
- [ ] All tasks can be saved and loaded
- [ ] File structure is organized
- [ ] UI is responsive and professional
- [ ] Error handling is in place
