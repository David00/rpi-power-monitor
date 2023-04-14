---
title: Test
layout: default
nav_exclude: true
search_exclude: true
redirect_from: 
  # - /docs/latest/test2
  # - docs/latest/test2
  # - /{{site.url}}/docs/latest/test2
  # - docs/latest/test2
  # - "{{site.url}}/docs/latest/test2"
  # - /{{ site.baseurl }}/docs/latest/test2
   - docs/latest/test2
   - "{{ '/docs/latest/test2' | absolute_url }}"
---


site.url = {{ site.url }}

site.baseurl = {{ site.baseurl }}

This page's front matter:

```
---
title: Test
layout: default
nav_exclude: true
search_exclude: true
redirect_from: 
#  - /{% raw %}{{site.baseurl}}{% endraw %}/docs/latest/test     # Works on localhost, doesn't work on Pages.
  - /docs/latest/test
#  - docs/latest/test    # Works on localhost, doesn't work on Pages.
---
```

[Link to https://david00.github.io/rpi-power-monitor/docs/latest/test2](https://david00.github.io/rpi-power-monitor/docs/latest/test2)