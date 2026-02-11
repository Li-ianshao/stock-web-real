# <!--<div x-data="{ open: true }" class="border rounded-lg shadow p-4 bg-white">
#                             <div class="flex justify-between items-center cursor-pointer" @click="open = !open">
#                                 <h3 class="text-lg font-semibold text-gray-800">關係人交易</h3>
#                                 <span x-text="open ? '－' : '+'" class="text-xl text-gray-600"></span>
#                             </div>
#                             <table class="w-full text-sm border-collapse">
#                             <caption class="text-left mb-2">SEC Form 4 常見 Transaction Codes 對照表（非完整，實際以 SEC 說明文件與表單註解為準）</caption>
#                             <thead class="bg-gray-50">
#                                 <tr>
#                                 <th class="px-3 py-2 border">代碼</th>
#                                 <th class="px-3 py-2 border">中文名稱</th>
#                                 <th class="px-3 py-2 border">英文</th>
#                                 <th class="px-3 py-2 border">說明</th>
#                                 <th class="px-3 py-2 border">投資解讀</th>
#                                 </tr>
#                             </thead>
#                             <tbody>
#                                 <tr>
#                                 <td class="px-3 py-2 border font-medium">P</td>
#                                 <td class="px-3 py-2 border">買進（公開市場/私下）</td>
#                                 <td class="px-3 py-2 border">Purchase</td>
#                                 <td class="px-3 py-2 border">內部人在市場或私下協議中直接買入公司股票。</td>
#                                 <td class="px-3 py-2 border">通常被視為「看多訊號」，但仍需搭配金額、持續性與角色（如 CEO/CFO）。</td>
#                                 </tr>
#                                 <tr>
#                                 <td class="px-3 py-2 border font-medium">S</td>
#                                 <td class="px-3 py-2 border">賣出（公開市場/私下）</td>
#                                 <td class="px-3 py-2 border">Sale</td>
#                                 <td class="px-3 py-2 border">內部人在市場或私下協議中賣出公司股票。</td>
#                                 <td class="px-3 py-2 border">未必是利空；可能為資產配置或個人現金需求，需看規模與是否連續賣出。</td>
#                                 </tr>
#                                 <tr>
#                                 <td class="px-3 py-2 border font-medium">A</td>
#                                 <td class="px-3 py-2 border">授予/獎勵</td>
#                                 <td class="px-3 py-2 border">Grant, Award, or Other Acquisition</td>
#                                 <td class="px-3 py-2 border">公司依薪酬計畫發放的 RSU/限制股/獎勵股等取得。</td>
#                                 <td class="px-3 py-2 border">屬於薪酬性質，通常不代表主觀看多或看空。</td>
#                                 </tr>
#                                 <tr>
#                                 <td class="px-3 py-2 border font-medium">M</td>
#                                 <td class="px-3 py-2 border">期權行使/衍生品轉換</td>
#                                 <td class="px-3 py-2 border">Option Exercise / Conversion of Derivative Security</td>
#                                 <td class="px-3 py-2 border">將員工期權、權證等衍生性商品轉換為普通股。</td>
#                                 <td class="px-3 py-2 border">多屬薪酬或既定合約安排；單看 M 不等於主動買進。</td>
#                                 </tr>
#                                 <tr>
#                                 <td class="px-3 py-2 border font-medium">F</td>
#                                 <td class="px-3 py-2 border">代扣稅/以股繳稅</td>
#                                 <td class="px-3 py-2 border">Payment of Tax Liability by Withholding/Delivering Shares</td>
#                                 <td class="px-3 py-2 border">RSU 歸屬或發放時，為繳稅而由公司扣回部分股份。</td>
#                                 <td class="px-3 py-2 border">行政動作，非主觀賣股；不宜解讀為看空。</td>
#                                 </tr>
#                                 <tr>
#                                 <td class="px-3 py-2 border font-medium">G</td>
#                                 <td class="px-3 py-2 border">贈與</td>
#                                 <td class="px-3 py-2 border">Gift</td>
#                                 <td class="px-3 py-2 border">無對價移轉（如贈與家人或信託）。</td>
#                                 <td class="px-3 py-2 border">通常與投資觀點無直接正負向含義。</td>
#                                 </tr>
#                                 <tr>
#                                 <td class="px-3 py-2 border font-medium">C</td>
#                                 <td class="px-3 py-2 border">轉換</td>
#                                 <td class="px-3 py-2 border">Conversion</td>
#                                 <td class="px-3 py-2 border">將可轉換證券（如可轉債、優先股）轉為普通股。</td>
#                                 <td class="px-3 py-2 border">結構性動作；需結合是否後續賣出來判斷。</td>
#                                 </tr>
#                                 <tr>
#                                 <td class="px-3 py-2 border font-medium">J</td>
#                                 <td class="px-3 py-2 border">其他（見註解）</td>
#                                 <td class="px-3 py-2 border">Other (explain in footnote)</td>
#                                 <td class="px-3 py-2 border">不屬於上述類別的特殊交易，通常會在備註/註解中說明細節。</td>
#                                 <td class="px-3 py-2 border">務必閱讀該 Form 4 的「Explanation of Responses」再做解讀。</td>
#                                 </tr>
#                             </tbody>
#                             </table>
#                             <p class="text-xs mt-2">
#                             備註：本表僅列常見代碼；實務上還有其他代碼與細分情境。解讀時請同時參考該次申報的表單欄位（如 Table I/II）與最下方的說明文字（Explanation of Responses）。
#                             </p>

#                             <div class="font-medium mb-1">Top institutional holders</div>
#                                 <div class="overflow-x-auto">
#                                 <table class="min-w-full text-left border">
#                                     <thead class="bg-gray-50">
#                                         <tr>
#                                             <th class="px-3 py-2 border">symbol</th>
#                                             <th class="px-3 py-2 border">name</th>
#                                             <th class="px-3 py-2 border">transaction</th>
#                                             <th class="px-3 py-2 border">share</th>
#                                             <th class="px-3 py-2 border">change</th>
#                                             <th class="px-3 py-2 border">price</th>
#                                             <th class="px-3 py-2 border">transactionDate</th>
#                                             <th class="px-3 py-2 border">filingDate</th>
#                                         </tr>
#                                     </thead>
#                                     <tbody>
#                                     ${data.Form4_transactions.map(s => `
#                                         <tr>
#                                             <td class="px-3 py-2 border">${s.symbol ?? ''}</td>
#                                             <td class="px-3 py-2 border">${s.name ?? ''}</td>
#                                             <td class="px-3 py-2 border">${s.transactionCode ?? ''}</td>
#                                             <td class="px-3 py-2 border">${s.share ?? ''}</td>
#                                             <td class="px-3 py-2 border">${s.change ?? ''}</td>
#                                             <td class="px-3 py-2 border">${s.transactionPrice ?? ''}</td>
#                                             <td class="px-3 py-2 border">${s.transactionDate ?? ''}</td>
#                                             <td class="px-3 py-2 border">${s.filingDate ?? ''}</td>
#                                         </tr>
#                                     `).join('')}
#                                     </tbody>
#                                 </table>
#                             </div>
#                         </div>-->