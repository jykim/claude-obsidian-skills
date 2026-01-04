# Gemini Image Generation Skill

Google Gemini API를 사용한 이미지 생성 스킬. 슬라이드 및 문서용 이미지를 생성합니다.

## Purpose

Gemini 2.0 Flash 또는 Imagen 3 모델을 사용하여 문서/슬라이드에 필요한 이미지를 생성합니다. 해상도와 종횡비 선택을 지원하며, 사용자 승인 워크플로우를 포함합니다.

## When to Use This Skill

- "Gemini로 이미지 생성해줘"
- "슬라이드용 그림을 Gemini API로 만들어줘"
- "프레젠테이션에 넣을 일러스트 생성"
- 무료 티어 이미지 생성이 필요할 때 (Gemini 2.0 Flash)
- 특정 종횡비가 필요할 때 (16:9, 9:16 등)

## Environment Setup

```bash
# 1. API 키 설정
export GEMINI_API_KEY="your-api-key"

# 2. 의존성 설치
pip install google-genai Pillow
```

## Workflow

### Phase 1: Analysis
1. 대상 문서/슬라이드 읽기
2. 이미지가 필요한 섹션/슬라이드 식별
3. 각 섹션의 핵심 컨셉 추출

### Phase 2: Style & Configuration Selection

**스타일 옵션:**

| # | 스타일 | 설명 | 적합한 용도 |
|---|--------|------|-------------|
| 1 | **Infographic (기본)** | 레이블/텍스트 포함, dense | **문서, 발표** |
| 2 | Technical Diagram | 깔끔한 선, 플로우차트 | 기술 문서 |
| 3 | Vibrant Modern Cartoon | 밝은 그라데이션, 플랫 | 비즈니스, 교육 |
| 4 | Professional Minimalist | 절제된 색상, 기하학 | 공식 발표 |
| 5 | Bold Graphic | 고대비, 팝아트 | 마케팅 |
| 6 | Custom | 사용자 지정 | 자유 |

> **기본값**: Infographic 스타일 (텍스트/레이블 포함)

**모델 선택:**

| 모델 | 비용 | 특징 |
|------|------|------|
| gemini-3-pro-image-preview | $0.06/장 | **기본값**, 한글 완벽, 최고 품질 |
| gemini-2.5-flash-image | $0.039/장 | 종횡비 지원, 빠름 |
| gemini-2.0-flash-exp | 무료 | 빠름, 반복용 (한글 깨짐) |
| imagen-4.0-generate-001 | $0.03/장 | Imagen 4.0, 고품질 |

**종횡비 옵션:** `1:1`, `9:16`, `16:9`, `3:4`, `4:3`, `3:2`, `2:3`, `21:9`

> **슬라이드용**: `--aspect-ratio 16:9` (기본 모델이 gemini-3-pro-image-preview)

### Phase 3: Image Generation

```bash
python3 "generate_gemini_image.py" \
    "[상세 설명]" \
    --output-path "[경로]" \
    --style "[스타일]" \
    --model "[모델]" \
    --aspect-ratio "[종횡비]" \
    --auto-approve
```

### Phase 4: Integration

**슬라이드:**
```markdown
![right fit](_files_/filename.png)
```

**문서:**
```markdown
![](path/to/image.png)
```

## Style Descriptions for Script

| 스타일 | --style 값 |
|--------|------------|
| **Infographic (기본)** | `"clean infographic with labeled sections, icons, and visual hierarchy"` |
| Technical Diagram | `"technical diagram with flowchart elements, arrows, and labeled components"` |
| Vibrant Modern Cartoon | `"vibrant modern minimalist cartoon illustration"` |
| Professional Minimalist | `"professional minimalist illustration with muted colors and clean geometric shapes"` |
| Bold Graphic | `"bold graphic illustration with high contrast colors and strong geometric shapes"` |

**프롬프트 작성 팁**:
- ✅ "4단계 프로세스를 보여주는 인포그래픽, 각 단계에 아이콘과 레이블"
- ✅ "비교 차트: A vs B, 장단점 표시"
- ❌ "두 사람이 연결된 추상적 일러스트" (의미 전달 어려움)

## File Naming Convention

**슬라이드:** `[slide-topic-slug].png`
- 예: `ai-changes-game.png`, `team-collaboration.png`
- 위치: 슬라이드와 같은 `_files_/` 디렉토리

**문서:** `[section-number]-[topic-slug].png`
- 예: `01-introduction.png`, `03-methodology.png`

## Cost Estimation

생성 전 비용 안내:
- Gemini 2.0 Flash: 무료
- Imagen 3: $0.03/장
- 예: "10장 생성 시 $0.30 (Imagen 3 기준)"

## Error Handling

| 에러 | 해결 방법 |
|------|-----------|
| API 키 없음 | `GEMINI_API_KEY` 환경변수 설정 |
| 안전 필터 차단 | 프롬프트 수정 후 재시도 |
| 모델 미지원 | 사용 가능한 모델로 변경 |
| 네트워크 오류 | 재시도 |

## Example Invocation

### 기본 사용

```bash
python3 generate_gemini_image.py "AI 지식 노동자가 책상에서 작업하는 모습" \
    --output-path "_files_/knowledge-worker.png"
```

### 16:9 슬라이드용 (권장)

```bash
python3 generate_gemini_image.py "팀 협업 미팅" \
    --output-path "_files_/team-meeting.png" \
    --model "gemini-2.5-flash-image" \
    --aspect-ratio "16:9" \
    --style "professional minimalist illustration"
```

### 고품질 이미지 (Imagen 4.0)

```bash
python3 generate_gemini_image.py "제품 쇼케이스" \
    --output-path "_files_/product.png" \
    --model "imagen-4.0-generate-001"
```

### 배치 처리 (자동 승인)

```bash
python3 generate_gemini_image.py "혁신 컨셉" \
    --output-path "_files_/innovation.png" \
    --auto-approve
```

## Best Practices

1. **인포그래픽 스타일 선호**: 텍스트/레이블 포함된 dense한 정보 시각화
2. **스타일 일관성**: 같은 문서/슬라이드 내에서 동일 스타일 유지
3. **상세한 프롬프트**: 구체적인 시각적 메타포와 컨셉 포함
4. **배치 생성**: 모든 이미지 먼저 생성 후 일괄 삽입
5. **비용 확인**: 생성 전 예상 비용 확인

> ⚠️ **피해야 할 것**: 추상적인 일러스트 (예: 사람들이 연결된 모호한 그림)
> ✅ **선호**: 다이어그램, 플로우차트, 레이블이 있는 인포그래픽

## Comparison with DALL-E Skill

| 기능 | DALL-E | Gemini |
|------|--------|--------|
| 무료 티어 | X | O (Flash) |
| 종횡비 | 정사각형만 | 5가지 옵션 |
| 출력 포맷 | JPEG | PNG/JPEG |
| 비용 | $0.04 | $0~$0.03 |

**선택 기준:**
- **DALL-E**: 검증된 품질, 기존 워크플로우
- **Gemini**: 무료 옵션 필요, 다양한 종횡비 필요
