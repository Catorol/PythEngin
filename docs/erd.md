# ERD

```mermaid
erDiagram
    creators ||--o{ videos : "публикует"
    products ||--o{ videos : "рекламируется в"
    videos ||--o{ video_hooks : "использует"
    hooks ||--o{ video_hooks : "применяется в"
    videos ||--o{ predictions : "получает"
    model_versions ||--o{ predictions : "выдаёт"

    creators {
        int id PK
        string external_id UK
        string tier
        string category
        string country
        bigint followers
        float engagement_rate
    }
    products {
        int id PK
        string external_id UK
        string category
        string subcategory
        string brand_type
        float price
        float rating
        int review_count
    }
    videos {
        int id PK
        string external_id UK
        int creator_id FK
        int product_id FK
        string video_format
        int length_seconds
        date published_at
        string status
        int viral_flag
        json features
    }
    hooks {
        int id PK
        string code UK
        string title
    }
    video_hooks {
        int video_id PK, FK
        int hook_id PK, FK
    }
    model_versions {
        int id PK
        string name
        string filename UK
        float roc_auc
        bool is_active
    }
    predictions {
        int id PK
        int video_id FK
        int model_version_id FK
        float probability
        int predicted_flag
        string recommendation
    }
```

## Сущности

- `creators`, `products`: справочники, у видео по одному из каждого (1:N).
- `videos`: ключевая сущность; `features` хранит снимок признаков модели для инференса.
- `hooks` и `video_hooks`: типы «хуков» и связь многие-ко-многим с видео.
- `model_versions`: загруженные модели, активна только одна (частичный уникальный индекс).
- `predictions`: история предсказаний.
