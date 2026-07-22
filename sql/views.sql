

CREATE OR REPLACE VIEW food_desert_score AS
WITH base AS (
    SELECT
        t.geoid,
        t.tract_name,
        t.total_pop,
        CASE WHEN f.urban THEN f.access_share_1mi
             ELSE f.access_share_10mi END AS access_raw,
        d.poverty_rate,
        d.pct_no_vehicle,
        f.lila_flag
    FROM tracts t
    JOIN food_access   f USING (geoid)
    JOIN demographics  d USING (geoid)
    WHERE t.total_pop > 0                      -- exclude empty tracts
      AND d.poverty_rate IS NOT NULL
      AND d.pct_no_vehicle IS NOT NULL
      AND (CASE WHEN f.urban THEN f.access_share_1mi
                ELSE f.access_share_10mi END) IS NOT NULL  -- no NULL scores
),
norm AS (
    SELECT
        geoid, tract_name, total_pop, lila_flag,
        access_raw, poverty_rate, pct_no_vehicle,
        (access_raw     - MIN(access_raw)     OVER ())
          / NULLIF(MAX(access_raw)     OVER () - MIN(access_raw)     OVER (), 0) AS access_n,
        (poverty_rate   - MIN(poverty_rate)   OVER ())
          / NULLIF(MAX(poverty_rate)   OVER () - MIN(poverty_rate)   OVER (), 0) AS poverty_n,
        (pct_no_vehicle - MIN(pct_no_vehicle) OVER ())
          / NULLIF(MAX(pct_no_vehicle) OVER () - MIN(pct_no_vehicle) OVER (), 0) AS vehicle_n
    FROM base
)
SELECT
    geoid, tract_name, total_pop, lila_flag,
    access_raw, poverty_rate, pct_no_vehicle,
    ROUND((100 * (0.40 * access_n + 0.35 * poverty_n + 0.25 * vehicle_n))::numeric, 1)
        AS composite_score
FROM norm;


CREATE OR REPLACE VIEW food_desert_tracts AS
WITH ranked AS (
    SELECT *, NTILE(4) OVER (ORDER BY composite_score) AS quartile
    FROM food_desert_score
)
SELECT
    geoid, tract_name, total_pop, lila_flag,
    access_raw, poverty_rate, pct_no_vehicle, composite_score,
    CASE quartile
        WHEN 4 THEN 'Severe'
        WHEN 3 THEN 'High'
        WHEN 2 THEN 'Moderate'
        ELSE 'Low'
    END AS severity_tier
FROM ranked;