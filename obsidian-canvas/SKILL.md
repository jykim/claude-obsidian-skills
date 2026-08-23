---
name: obsidian-canvas
description: Create and manage Obsidian Canvas files with automatic layout generation. Use when creating visual knowledge maps, weekly reading summaries, or project timelines.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
license: MIT
---

# Obsidian Canvas Skill

Create visual canvases with automatic layout, color-coding, and smart node positioning.

## When to Use This Skill

Activate when you need to:
- Create visual summaries of weekly reading
- Build knowledge maps connecting related topics
- Design project timelines or mind maps
- Organize scattered notes into visual structure

## Core Principle: Automatic Layout

> **레이아웃은 자동으로, 콘텐츠에 집중하라**

Canvas의 핵심은 노드 배치와 연결. 수동으로 좌표 계산하는 대신, 패턴별 자동 레이아웃 사용.

## Edit Workflow: Draft & Atomic Replace (CRITICAL)

> **캔버스 파일을 직접 여러 번 덮어쓰지 마라.**

Obsidian이 캔버스 탭을 열어둔 상태에서 외부에서 `.canvas` 파일을 수정하면, Obsidian이 자기 메모리의 (종종 minimal한) 상태로 디스크를 다시 덮어써 작업 결과가 사라질 수 있다.

### 권장 워크플로우

1. **임시 파일에서 편집 완료**: `<원본>.canvas.draft`에 모든 노드·엣지·컨테이너를 한 번에 작성
2. **검증**: JSON 유효성, 노드 좌표 오버랩, 엣지 ID 매칭 확인
3. **Atomic Replace**: `mv draft → 원본` 한 번의 파일 시스템 이벤트로 교체
4. **결과 확인**: `wc -l`로 파일 크기 검증 (minimal 상태 = 빈 캔버스 의심)

### 피해야 할 패턴

- 같은 `.canvas` 파일에 연속적으로 Write 호출 (race condition)
- Edit으로 부분 수정 후 Obsidian sync 전 다음 Edit
- 작성 직후 바로 `obsidian://open` 호출 (작성 중 sync 충돌 가능)
- 사용자에게 "Obsidian 새로고침" 반복 요청

### Atomic Replace 예시

```bash
# 1. 임시 파일에 완전한 캔버스 작성
Write file: AI/Canvas/foo.canvas.draft (전체 내용)

# 2. 한 번에 교체
mv "AI/Canvas/foo.canvas.draft" "AI/Canvas/foo.canvas"

# 3. 결과 검증
wc -l "AI/Canvas/foo.canvas"  # 정상 = 노드 수에 비례한 줄 수
                              # 비정상 = 6-9줄 (minimal 상태)
```

### 작은 수정도 전체 재작성

부분 수정이 필요해도 **전체 캔버스 JSON을 임시 파일에 다시 쓰고 atomic replace**. Edit 도구로 한 노드만 수정하는 패턴은 sync 충돌을 일으킬 수 있다.

## Canvas File Structure

```json
{
  "nodes": [
    {
      "id": "unique-id",
      "type": "text" | "file" | "link" | "group",
      "text": "content or file path",
      "x": 0, "y": 0,
      "width": 250, "height": 60,
      "color": "1-6"
    }
  ],
  "edges": [
    {
      "id": "edge-id",
      "fromNode": "node-id",
      "fromSide": "top|bottom|left|right",
      "toNode": "node-id",
      "toSide": "top|bottom|left|right",
      "color": "1-6"
    }
  ]
}
```

## Layout Patterns

### 1. Radial Layout (방사형)
중심 노드에서 카테고리별로 방사형 배치

```
        Topic1
           |
Topic4 - CENTER - Topic2
           |
        Topic3
```

**Use case**: Weekly reading, topic overview
**Spacing**: 400-600px from center

### 2. Grid Layout (그리드)
카테고리별 세로 열로 배치

```
Category1  Category2  Category3
  Item1      Item1      Item1
  Item2      Item2      Item2
  Item3      Item3      Item3
```

**Use case**: Comparative analysis, multi-column organization
**Spacing**: X: 400px, Y: 100px between items

### 3. Timeline Layout (타임라인)
시간순 가로 흐름

```
Event1 → Event2 → Event3 → Event4
```

**Use case**: Project milestones, historical events
**Spacing**: 300px horizontal

### 4. Hierarchical Layout (계층형)
트리 구조로 위→아래 확장

```
         Root
        /    \
    Child1  Child2
     / \      / \
   A   B    C   D
```

**Use case**: Concept breakdown, org charts
**Spacing**: Y: 200px per level

### 5. Side-by-side Comparison (가로 비교)
관련 항목들을 가로로 배치하여 한눈에 비교

```
┌─────────┐ ┌─────────┐ ┌─────────┐
│  항목1  │ │  항목2  │ │  항목3  │
│ (350px) │ │ (350px) │ │ (350px) │
└─────────┘ └─────────┘ └─────────┘
```

**Use case**: 옵션 비교, 요약 카드, 관련 개념 나열
**Node width**: 300-350px (좁게)
**X spacing**: 40px between nodes
**X position calculation** (centered at x=0):
- 2 nodes: x = -195, 195
- 3 nodes: x = -390, 0, 390
- 계산식: 첫 노드 x = -(총너비/2) + (노드너비/2)

### 6. Two-Column Comparison (2열 비교)
대조되는 두 관점/옵션을 양쪽에 배치

```
    LEFT COLUMN          RIGHT COLUMN
    ┌─────────┐          ┌─────────┐
    │ Header  │          │ Header  │
    ├─────────┤          ├─────────┤
    │ Item 1  │          │ Item 1  │
    │ Item 2  │          │ Item 2  │
    │ Item 3  │          │ Item 3  │
    └────┬────┘          └────┬────┘
         └───────┬───────────┘
           ┌─────┴─────┐
           │  Common   │
           │  Ground   │
           └───────────┘
```

**Use case**: A vs B 비교, 찬반, Before/After, 관점 대조
**Column width**: 500-550px each
**X spacing**: 750px between column centers (left: -375, right: 375)
**Center elements**: x = 0 (양쪽 연결)

## Color Scheme

| Color | ID | Use Case |
|-------|-----|----------|
| Red | 1 | AI & Tech |
| Orange | 2 | Work & Projects |
| Yellow | 3 | Current Events |
| Green | 4 | PKM & Learning |
| Purple | 5 | Personal & Meta |
| Blue | 6 | Education & Career |

## Node Types & Sizes

### Text Node
- **Default**: 250x60 (single line)
- **Quote**: 280x60 (wider for readability)
- **Multi-line**: 250x(60 + 20*lines)

### File Node
- **Link to note**: 280x90 (includes title + summary)
- **Path format**: Use wiki links in text field

### Group Node
- **Category header**: 200x50
- **Container**: Auto-size based on children

### Width Adaptation (폭 변경 시 콘텐츠 조정)

레이아웃 변경으로 노드 폭이 줄어들 때:

| 폭 변경 | 콘텐츠 조정 |
|--------|------------|
| 550px → 350px | 테이블 열 축소, 긴 문장 분리 |
| 350px → 300px | 불릿 2-3개만, 예시 제거 |
| 300px → 250px | 제목 + 한 줄 요약만 |

**축약 우선순위** (먼저 제거할 것):
1. 부연 설명, 괄호 내용
2. 예시, 참조
3. 테이블 행 (핵심만 유지)
4. 불릿 포인트 수

## Auto-Layout Algorithm

### Step 1: Categorize Nodes
Group nodes by topic/category using tags or manual grouping.

### Step 2: Calculate Positions
Based on layout pattern:
- **Radial**: Divide 360° by category count
- **Grid**: Calculate column width, row height
- **Timeline**: Distribute evenly on X-axis
- **Hierarchy**: BFS traversal, level-by-level

### Step 3: Avoid Overlaps
- Minimum spacing: 50px
- Check bounding boxes
- Adjust if collision detected

### Step 4: Create Edges
- Connect center to categories (radial)
- Connect sequential items (timeline)
- Connect parent-child (hierarchy)

## Example Templates

### Weekly Reading Canvas

```json
{
  "nodes": [
    {
      "id": "center",
      "type": "text",
      "text": "# Weekly Reading\n## Dec 20-27, 2025",
      "x": 0, "y": 0,
      "width": 200, "height": 80,
      "color": "5"
    },
    {
      "id": "group-ai",
      "type": "text",
      "text": "## AI & Learning",
      "x": -380, "y": -200,
      "width": 180, "height": 50,
      "color": "1"
    }
  ],
  "edges": [
    {
      "id": "edge-center-ai",
      "fromNode": "center",
      "fromSide": "left",
      "toNode": "group-ai",
      "toSide": "right",
      "color": "1"
    }
  ]
}
```

### Project Timeline Canvas

```json
{
  "nodes": [
    {
      "id": "phase1",
      "type": "text",
      "text": "**Phase 1**\nResearch",
      "x": 0, "y": 0,
      "width": 200, "height": 80,
      "color": "1"
    },
    {
      "id": "phase2",
      "type": "text",
      "text": "**Phase 2**\nDevelopment",
      "x": 300, "y": 0,
      "width": 200, "height": 80,
      "color": "2"
    }
  ],
  "edges": [
    {
      "id": "edge-1-2",
      "fromNode": "phase1",
      "fromSide": "right",
      "toNode": "phase2",
      "toSide": "left"
    }
  ]
}
```

## Best Practices

### Content First, Layout Second
1. List all items to include
2. Group by category/theme
3. Choose layout pattern
4. Generate coordinates
5. Add edges last

### Keep It Scannable
- Max 20 nodes per canvas
- 4-6 categories ideal
- Clear visual hierarchy
- Consistent spacing

### Link to Notes
- Use wiki link format: `[[Note Title]]`
- Include section links: `[[Note#Section]]`
- Add emoji for visual cues

### Iterate Layout
- Start with template
- Adjust spacing if crowded
- Test in Obsidian preview
- Refine edge routing

### Part Headers for Long Documents
긴 캔버스는 Part 헤더로 섹션 구분

**언제 사용**:
- 노드 수 15개 이상
- 논리적으로 구분되는 단계/섹션 존재

**Part 헤더 형식**:
```json
{"id":"part1","type":"text","text":"# 📋 Part 1: [섹션명]","x":-275,"y":[y],"width":550,"height":60,"color":"[색상]"}
```

**Part 간 색상 구분**:
- 각 Part에 다른 색상 할당
- Part 내 노드들은 동일 색상 계열 사용
- 시각적 네비게이션 향상

## Overlap Prevention (오버랩 방지)

캔버스 업데이트 시 **항상** 오버랩을 체크해야 한다. 오버랩은 가독성을 해치고 노드 선택을 어렵게 만든다.

### 오버랩 계산 공식

두 노드가 겹치는지 확인:
```
Node A: (x1, y1, width1, height1)
Node B: (x2, y2, width2, height2)

오버랩 조건 (둘 다 만족 시 오버랩):
- X축: x1 < x2 + width2 AND x1 + width1 > x2
- Y축: y1 < y2 + height2 AND y1 + height1 > y2
```

### 적정 간격 계산

노드 간 간격을 유지하기 위한 공식:
```
다음 노드 Y = 현재 노드 Y + 현재 노드 Height + Gap(30-50px)

예시:
- Node A: y=500, height=180 → Node A 하단 = 680
- Node B 시작: y = 680 + 40(gap) = 720
```

### 노드 높이 권장 기준

| 콘텐츠 유형 | 권장 높이 |
|------------|----------|
| 한 줄 제목 | 60-80px |
| 2-3줄 텍스트 | 100-120px |
| 중간 설명 (4-6줄) | 140-180px |
| 긴 설명 (7-10줄) | 200-260px |
| 테이블 포함 | 250-350px |

### 캔버스 수정 시 체크리스트

1. **수정 전**: 현재 노드들의 Y 좌표 + Height 파악
2. **노드 추가 시**: 삽입 위치 기준 하단 모든 노드 Y값 조정
3. **Height 변경 시**: 해당 노드 이후 모든 노드 Y값 재계산
4. **수정 후**: 모든 인접 노드 쌍에 대해 오버랩 검사

### 레이아웃 패턴별 간격

| 레이아웃 | X 간격 | Y 간격 |
|---------|--------|--------|
| Radial | 400-600px | N/A |
| Grid | 350-450px | 40-60px |
| Timeline | 280-350px | N/A |
| Hierarchical | N/A | 150-250px |
| Two-Column | 500-700px | 40-60px |

### 자동 오버랩 수정 절차

```
1. 모든 노드를 Y 좌표 기준 정렬
2. 각 노드에 대해:
   a. 이전 노드의 하단(y + height)과 현재 노드의 상단(y) 비교
   b. 겹치면: 현재 노드 y = 이전 노드 하단 + 40px
   c. 이후 모든 노드 y 값을 동일 delta만큼 이동
3. 센터 정렬이 필요한 노드는 x 값도 조정
```

## Quality Checklist

Before finalizing canvas:

- [ ] All nodes have unique IDs
- [ ] **No overlapping nodes** (run overlap check formula above)
- [ ] Minimum 30-50px spacing between adjacent nodes
- [ ] Colors follow scheme (AI=1, PKM=4, etc.)
- [ ] Center node clearly visible
- [ ] Edges don't cross unnecessarily
- [ ] Wiki links are valid
- [ ] Canvas renders in Obsidian without errors

## Common Use Cases

### 1. Weekly Reading Summary
- **Layout**: Radial
- **Categories**: AI, PKM, Current Events, Education
- **Nodes**: Article links with quotes
- **Output**: `AI/Canvas/YYYY-MM-DD Weekly Reading.canvas`

### 2. Project Planning
- **Layout**: Timeline or Hierarchical
- **Nodes**: Milestones, tasks, deliverables
- **Colors**: By status or phase
- **Output**: `Projects/[Name]/Planning.canvas`

### 3. Concept Map
- **Layout**: Hierarchical
- **Nodes**: Main concept + subconcepts
- **Edges**: Parent-child relationships
- **Output**: `Topics/[Category]/[Concept].canvas`

### 4. Meeting Network
- **Layout**: Radial
- **Center**: Person or topic
- **Nodes**: Related meetings/people
- **Output**: `AI/Canvas/[Topic] Network.canvas`

## Tools & Functions

### generate_radial_layout(center, categories, items_per_category)
Returns node positions in radial pattern.

### generate_grid_layout(columns, items)
Returns node positions in grid.

### create_edge(from_id, to_id, color)
Returns edge object with auto-routing.

### validate_canvas(canvas_json)
Checks for overlaps, invalid IDs, broken links.

## Error Handling

### Common Issues
- **Overlapping nodes**: Increase spacing or use different layout
- **Broken wiki links**: Validate file exists before linking
- **Edge routing**: Simplify connections, avoid crossing

### Debugging
- Use Obsidian developer console (Cmd+Opt+I)
- Check JSON syntax
- Verify all node IDs exist in edges

---

**Next Steps**: Run example canvas generation to test layout algorithms.
