$httpClient.get({url:"https://my.ippure.com/v1/info", timeout: 3000}, (error, resp, data) => {
  if (error) {
    $ui.alert("查询失败：" + error);
    $done();
    return;
  }
  try {
    const i = JSON.parse(data);
    let body = [
      `IP        : ${i.ip ?? "Unknown"}`,
      `定位      : ${[i.city, i.region, i.countryCode].filter(Boolean).join(", ") || "Unknown"}`,
      `组织      : ${i.asOrganization || "Unknown"}`,
      `属性      : ${(i.isBroadcast ? "广播" : "原生")} / ${(i.isResidential ? "住宅" : "机房")}`,
      `风控      : ${i.fraudScore ?? "N/A"}`
    ].join("\n");
    
    $ui.alert(body);
    $done();
  } catch(e) {
    $ui.alert("解析失败：" + e);
    $done();
  }
});
