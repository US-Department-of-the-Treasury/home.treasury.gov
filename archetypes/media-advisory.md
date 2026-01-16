---
title: "{{ replace .Name "-" " " | title }}"
date: {{ .Date }}
draft: false
type: news
url: /news/media-advisories/{{ .Name | urlize }}/
---

