---
title: "PurS3 Lab - Readings"
layout: textlay
excerpt: "Reading resources on research, PhD, and advising."
sitemap: false
permalink: /readings
---

# Readings

A collection of reading resources we find useful on doing research, pursuing a PhD, advising, and more.

{% for section in site.data.readings %}
### {{ section.category }}

{% for item in section.items %}
* [{{ item.title }}]({{ item.url }}){% if item.author %} by {{ item.author }}{% endif %}
{% endfor %}
{% endfor %}
