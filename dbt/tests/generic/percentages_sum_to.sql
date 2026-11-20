{#- Fails for rows where a set of percentage columns does not add up to the
    target (100) within a tolerance. Rows with any missing value are skipped. -#}
{% test percentages_sum_to(model, columns, target=100, tolerance=2) %}
select *
from {{ model }}
where {% for c in columns %}{{ c }} is not null{% if not loop.last %} and {% endif %}{% endfor %}
  and abs(({% for c in columns %}{{ c }}{% if not loop.last %} + {% endif %}{% endfor %}) - {{ target }}) > {{ tolerance }}
{% endtest %}
