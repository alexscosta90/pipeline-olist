-- Grão: uma linha por UF do cliente.
WITH entregas_por_pedido AS (
    -- Grão: um pedido entregue com data efetiva de entrega.
    SELECT
        c.estado AS uf,
        date_diff('day', p.data_compra, p.data_entrega_cliente) AS dias_entrega
    FROM refined.pedidos AS p
    JOIN refined.clientes AS c ON c.cliente_id = p.cliente_id
    WHERE p.status = 'delivered'
      AND p.data_entrega_cliente IS NOT NULL
)
SELECT
    uf,
    count(*) AS entregues,
    round(avg(dias_entrega), 1) AS dias_medio,
    median(dias_entrega) AS dias_mediana
FROM entregas_por_pedido
GROUP BY uf
ORDER BY dias_medio
