-- Grão: um tipo de pagamento.
-- Pagamentos pode incluir frete; o mart 01 define receita como a soma do preço dos itens.
-- Pedidos pode somar acima do total válido porque um pedido pode usar mais de um tipo.
WITH pagamentos_validos AS (
    -- Grão: um registro de pagamento de pedido válido.
    SELECT
        pg.pedido_id,
        pg.pagamento_seq,
        pg.tipo,
        pg.valor
    FROM refined.pagamentos AS pg
    JOIN refined.pedidos    AS p ON p.pedido_id = pg.pedido_id
    WHERE p.status NOT IN ('canceled', 'unavailable')
),
por_tipo AS (
    -- Grão: um tipo de pagamento.
    SELECT
        tipo,
        count(*)                  AS pagamentos,
        count(DISTINCT pedido_id) AS pedidos,
        sum(valor)                AS valor
    FROM pagamentos_validos
    GROUP BY tipo
),
total_pagamentos AS (
    -- Grão: o total de valores pagos, uma linha.
    SELECT sum(valor) AS valor_total
    FROM pagamentos_validos
)
SELECT
    p.tipo,
    p.pagamentos,
    p.pedidos,
    p.valor,
    round(100.0 * p.valor / t.valor_total, 1) AS pct_valor
FROM por_tipo AS p
CROSS JOIN total_pagamentos AS t
ORDER BY pct_valor DESC

-- O total pago pode superar a receita do mart 01 porque o mart 01
-- soma preco dos itens, enquanto pagamentos registra o valor efetivamente pago,
-- que pode incluir frete.