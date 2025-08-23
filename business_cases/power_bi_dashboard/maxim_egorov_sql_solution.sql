-- In each survey, comapare the votes for courses and assign points, sum points per course, and order courses by popularity

SELECT
    c.course_id,
    c.course_name,
    COALESCE(SUM(sp.points), 0) AS popularity_points  
FROM
    course c
LEFT JOIN
(
    SELECT
        course_name,
        CASE
            WHEN ABS(votes_a - votes_b) <= 0.05 * (votes_a + votes_b) THEN 0.5
            WHEN winner = course_name THEN 1
            ELSE 0
        END AS points
    FROM
    (   
        SELECT
            option_a AS course_name,
            votes_a,
            votes_b,
            CASE
                WHEN votes_a > votes_b THEN option_a
                ELSE option_b
            END AS winner
        FROM survey

        UNION ALL

        SELECT
            option_b AS course_name,
            votes_a,
            votes_b,
            CASE
                WHEN votes_a > votes_b THEN option_a
                ELSE option_b
            END AS winner
        FROM survey
    ) sub
) sp
    ON c.course_name = sp.course_name  
GROUP BY
    c.course_id,
    c.course_name
ORDER BY
    popularity_points DESC