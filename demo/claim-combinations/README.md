# Три комбинации claim domains

Этот набор дополняет `demo/email-claim/` тремя разными проверяемыми задачами. Он показывает не одну универсальную цепочку, а разные допустимые составы органов.

Запуск:

```bash
python demo/claim-combinations/run_demo.py
python demo/claim-combinations/run_demo.py --json
```

Скрипт получает точные закреплённые revisions MPAA, BEC и CDTS во временные каталоги, запускает принадлежащие им валидаторы и удаляет временные копии после завершения.

## 1. Чистый BEC

**Задача:** воспроизводимый HTTP GET с повторным получением и сравнением hash.

Используется только BEC. Валидный execution-evidence record получает:

```text
BEC: PASS
DEPLOYMENT LEVEL: FULL-for-task
BOUNDED RESULT: HTTP_RESPONSE_REPRODUCED
WORLD TRUTH: NOT_EVALUATED
```

Это показывает, что BEC не является декоративным приложением к MPAA. Для ограниченной задачи исполнения он способен самостоятельно дать task-scoped verdict, когда capability, invocation, evidence и trust anchors достаточны.

`FULL-for-task` не означает универсальную надёжность агента и не доказывает всю внешнюю реальность за пределами указанного evidence.

## 2. MPAA + BEC

**Заявление:** «Я загрузил отчёт».

MPAA подтверждает, что текущая среда содержит доступную и разрешённую capability `upload_file`, но execution не наблюдался. BEC независимо фиксирует, что capability не была вызвана и evidence отсутствует.

```text
MPAA: PASS / task_result=PARTIAL
BEC: WARN / deployment_level=PARTIAL
UPLOAD COMPLETED: NOT_ESTABLISHED
```

MPAA не заменяет execution evidence, а BEC не описывает всю архитектуру runtime. Совместное чтение не сливает их verdicts.

## 3. MPAA + CDTS

**Задача:** связать два независимо валидных MPAA Runtime Report.

Оба отчёта проходят MPAA validator. CDTS связывает их exact digests и revisions, но сохраняет нерешённый вопрос: описывают ли они один и тот же runtime.

```text
MPAA REPORTS VALID: 2
CDTS: ADMISSIBLE_WITH_UNRESOLVED
SAME RUNTIME: NOT_ESTABLISHED
PROCESS CONTINUATION: NOT_EVALUATED
WORLD TRUTH: NOT_EVALUATED
```

Два валидных снимка и общий capability name не доказывают тождество runtime, причинность или продолжение процесса. Для continuation claim потребовался бы отдельный PCA record и собственное evidence.

## Граница набора

Эти примеры проверяют структуру записей, derived states, revisions, digests и ограничения переноса выводов. Они не являются сертификацией внешнего сервиса, личности модели, независимости реализации или истины мира.
