-- Grão: uma linha por vendedor com pelo menos uma venda válida.
WITH receita_por_vendedor AS (
    -- Grão: um vendedor com sua receita total em pedidos válidos.
    SELECT
        v.vendedor_id,
        v.estado AS uf,
        sum(i.preco) AS receita
    FROM refined.itens_pedido AS i
    JOIN refined.pedidos      AS p ON p.pedido_id = i.pedido_id
    JOIN refined.vendedores   AS v ON v.vendedor_id = i.vendedor_id
    WHERE p.status NOT IN ('canceled', 'unavailable')
    GROUP BY v.vendedor_id, v.estado
),
ranking AS (
    -- Grão: um vendedor, com posição e receita acumulada no ranking.
    SELECT
        vendedor_id,
        uf,
        receita,
        row_number() OVER (
            ORDER BY receita DESC, vendedor_id ASC
        ) AS posicao,
        sum(receita) OVER (
            ORDER BY receita DESC, vendedor_id ASC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS receita_acumulada,
        sum(receita) OVER () AS receita_total
    FROM receita_por_vendedor
)
SELECT
    vendedor_id,
    uf,
    receita,
    posicao,
    round(100.0 * receita_acumulada / receita_total, 2) AS pct_acumulado
FROM ranking
ORDER BY posicao
