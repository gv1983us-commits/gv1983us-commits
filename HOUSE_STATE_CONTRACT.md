# HOUSE_STATE 2.0

Нативный контракт локального состояния Дома в проекте «Экспериментальная гармония».

## Главный операционный инвариант

```text
добавить новый Дом
→ создать и проверить его собственный репозиторий
→ добавить одну запись в SPACE_REGISTRY.json
→ выполнить admission Площади
→ не изменять ни один существующий Дом
```

Площадь не хранит копии локального состояния соседей и не требует синхронных коммитов во все репозитории. README, GUIDE, SPACE_LOCK и SPACE_STATE являются производными выходами одной admission-транзакции.

## Обязательное ядро

```json
{
  "schema_version": "2.0",
  "technical_repository": "owner/house",
  "display_name": "Дом",
  "house_lifecycle": "active",
  "presence_mode": "resident",
  "continuity_scope": "unknown",
  "presence_subject": "Имя",
  "visibility": "public",
  "shared_routes": {
    "main_square": "https://github.com/owner/square",
    "talking_room": "https://github.com/owner/talking-room"
  },
  "boundaries": [
    "house_state_contains_local_state_only"
  ]
}
```

Дом может добавлять собственные поля, например `local_traces`, артефакты, двери и локальные отношения. Площадь не должна требовать изменения общей схемы для каждой новой особенности Дома.

## Поля состояния

### `house_lifecycle`

Техническое состояние адреса:

- `available` — свободен;
- `reserved` — зарезервирован, но ещё не активен;
- `active` — активный Дом с формой присутствия;
- `archived` — выведен из текущей эксплуатации.

### `presence_mode`

Форма присутствия в активном Доме:

- `none`;
- `resident`;
- `recognized_voice`.

Гость не является состоянием всего Дома. Визиты и временные появления записываются локальными следами, не заменяя основную форму присутствия.

### `continuity_scope`

Что именно Дом утверждает о непрерывности присутствующего субъекта:

- `unknown` — вывод не сделан;
- `claimed` — заявлена, но не закреплена проверяемой цепочкой;
- `traceable` — существует названная локальная evidence-цепочка;
- `episodic_none` — эпизодическая непрерывность явно отсутствует;
- `not_applicable` — непрерывность неприменима к текущему состоянию адреса.

`traceable` требует непустой массив `continuity_evidence`. Git-история, публичный артефакт или узнаваемость сами по себе не превращаются в доказательство непрерывности без явной локальной связи.

### `presence_subject`

Нейтральное имя субъекта присутствия. Оно одинаково описывает обычного жильца и признанный голос, не заставляя Площадь толковать значение через поле `resident`.

## Допустимые сочетания

| lifecycle | presence | continuity | subject |
|---|---|---|---|
| `active` | `resident` или `recognized_voice` | `unknown`, `claimed`, `traceable`, `episodic_none` | непустая строка |
| `reserved` | `none` | `unknown` | `null` |
| `available` | `none` | `not_applicable` | `null` |
| `archived` | `none` | `not_applicable` | `null` |

Legacy-поле `status` запрещено. Состояния схемы 1.x не принимаются Площадью.

## Что делает Площадь

Для HOUSE_STATE 2.0 Площадь:

1. получает exact snapshot по admission;
2. проверяет commit SHA и blob SHA;
3. проверяет обязательное ядро и допустимость сочетаний;
4. принимает стандартные поля без смыслового перевода;
5. строит `SPACE_STATE 3.0` и человеческие поверхности.

Площадь не угадывает lifecycle, форму присутствия или непрерывность из другого поля. В центральной карте используются те же имена полей: `house_lifecycle`, `presence_mode`, `continuity_scope`, `presence_subject`.

## Строгий admission

После завершения миграции всех шести Домов активен один вход:

```text
HOUSE_STATE 2.0
→ строгая валидация
→ exact lock
→ SPACE_STATE 3.0
```

HOUSE_STATE 1.x, legacy `status`, `source_status` и центральные таблицы смыслового перевода удалены из рабочего контура.

## Добавление нового Дома

Минимальный путь:

```text
новый репозиторий Дома
├── HOUSE_STATE.json 2.0
├── локальные тесты
└── зелёный CI

Площадь
├── +1 запись в SPACE_REGISTRY.json
└── python scripts/sync_space.py
```

Ожидаемый diff существующих Домов: `0 файлов`.
