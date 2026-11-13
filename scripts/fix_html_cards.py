"""Complete fix v2."""
html_path = 'miniapp/webapp/index.html'
content = open(html_path, encoding='utf-8').read()

print('adminCardsPanel count:', content.count('adminCardsPanel'))

# Find the target context
idx = content.find('adminSaveNftCaseChancesBtn')
snippet = repr(content[idx:idx+400])
print('Context:', snippet)

CARD_PANEL = '''
              <article class="cardish panel full-row" id="adminCardsPanel">
                <div class="panel-head">
                  <div class="panel-title-group">
                    <span class="eyebrow">Переключение реквизитов</span>
                    <h2>💳 Mono карты</h2>
                  </div>
                  <span class="hint" id="adminActiveCardBadge">Загрузка...</span>
                </div>
                <div class="inline-grid compact-2" style="margin-bottom: 14px;">
                  <label>Карта 1
                    <input type="text" id="adminCard1Input" placeholder="4874 0000 0000 0000" />
                  </label>
                  <label>Карта 2
                    <input type="text" id="adminCard2Input" placeholder="5375 0000 0000 0000" />
                  </label>
                </div>
                <div class="actions" style="display:flex; flex-wrap:wrap; gap:8px;">
                  <button class="primary" type="button" onclick="handleSwitchCard(1)">✅ Активировать карту 1</button>
                  <button class="primary" type="button" onclick="handleSwitchCard(2)">✅ Активировать карту 2</button>
                  <button class="ghost" type="button" onclick="handleSaveCards()">💾 Сохранить номера карт</button>
                </div>
              </article>'''

# The actual target (with double close):
TARGET = '''              </article>
            </div>
          </div>

            </div>
          </div>

          <!-- Вкладка 3: Игры и RTP -->'''

REPLACEMENT = '              </article>' + CARD_PANEL + '''
            </div>
          </div>

          <!-- Вкладка 3: Игры и RTP -->'''

if TARGET in content:
    content = content.replace(TARGET, REPLACEMENT, 1)
    print('Inserted! adminCardsPanel count =', content.count('adminCardsPanel'))
    open(html_path, 'w', encoding='utf-8').write(content)
    print('Saved.')
else:
    print('Target still not found')
    # Try without the extra indented divs
    TARGET2 = '              </article>\n            </div>\n          </div>\n\n            </div>\n          </div>\n\n          <!-- Вкладка 3'
    if TARGET2 in content:
        REPL2 = '              </article>' + CARD_PANEL + '\n            </div>\n          </div>\n\n          <!-- Вкладка 3'
        content = content.replace(TARGET2, REPL2, 1)
        print('Inserted via alt target! adminCardsPanel count =', content.count('adminCardsPanel'))
        open(html_path, 'w', encoding='utf-8').write(content)
        print('Saved.')
    else:
        print('Alt target also not found')
