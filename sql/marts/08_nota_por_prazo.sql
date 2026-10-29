-- Grão: uma linha por situação de entrega.
WITH nota_pedido AS (
    -- Grão: um pedido avaliado, com a média de suas avaliações.
    SELECT
        pedido_id,
        avg(nota) AS nota
    FROM refined.avaliacoes
    GROUP BY pedido_id
),
pedidos_classificados AS (
    -- Grão: um pedido entregue, com data efetiva e avaliação.
    SELECT
        p.pedido_id,
        CASE
            WHEN p.data_entrega_cliente::DATE <= p.data_entrega_prevista THEN 'no_prazo'
            ELSE 'atrasado'
        END AS situacao,
        n.nota
    FROM refined.pedidos AS p
    JOIN nota_pedido    AS n ON n.pedido_id = p.pedido_id
    WHERE p.status = 'delivered'
      AND p.data_entrega_cliente IS NOT NULL
),
por_situacao AS (
    -- Grão: uma situação de entrega.
    SELECT
        situacao,
        count(*) AS pedidos_avaliados,
        round(avg(nota), 2) AS nota_media,
        round(
            100.0 * sum(CASE WHEN nota <= 2 THEN 1 ELSE 0 END) / count(*),
            1
        ) AS pct_nota_baixa
    FROM pedidos_classificados
    GROUP BY situacao
)
SELECT
    situacao,
    pedidos_avaliados,
    nota_media,
    pct_nota_baixa
FROM por_situacao
ORDER BY situacao
