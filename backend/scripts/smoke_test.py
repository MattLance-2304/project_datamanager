"""后端全流程冒烟测试：SQLite + TestClient，无需数据库和 Docker。

运行：backend/.venv/Scripts/python scripts/smoke_test.py
"""
import hashlib
import io
import os
import shutil
import sys
import time
import uuid
from pathlib import Path

# 必须在导入 app 之前设置环境
BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_DB = BACKEND_DIR / "test_rdms.db"
TEST_DATA = BACKEND_DIR / "test_data"
if TEST_DB.exists():
    TEST_DB.unlink()
shutil.rmtree(TEST_DATA, ignore_errors=True)

os.environ["RDMS_DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["RDMS_DATA_DIR"] = str(TEST_DATA)
os.environ["RDMS_JWT_SECRET"] = "test-secret"

sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
client.__enter__()  # 触发 lifespan：建表 + 种子数据

PASSED = 0
FAILED = []


def check(name: str, cond: bool, extra: str = ""):
    global PASSED
    if cond:
        PASSED += 1
        print(f"  PASS  {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL  {name}  {extra}")


def make_png(w=64, h=48, color=(200, 30, 30)) -> bytes:
    img = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def upload_bytes(data: bytes, filename: str, headers: dict) -> dict:
    """走完整分片上传协议。"""
    r = client.post("/api/uploads", json={"filename": filename, "size": len(data)}, headers=headers)
    assert r.status_code == 200, r.text
    upload_id = r.json()["upload_id"]
    chunk = 5 * 1024 * 1024
    for i in range(0, max(1, (len(data) + chunk - 1) // chunk)):
        client.put(f"/api/uploads/{upload_id}/{i}", data=data[i * chunk:(i + 1) * chunk],
                   headers=headers)
    r = client.post(f"/api/uploads/{upload_id}/complete", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def main():
    print("== 1. 登录与用户 ==")
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    check("管理员登录", r.status_code == 200, r.text)
    token = r.json()["token"]
    H = {"Authorization": f"Bearer {token}"}
    check("登录返回 admin 角色", r.json()["user"]["role"] == "admin")

    r = client.get("/api/auth/me", headers=H)
    check("获取当前用户", r.status_code == 200 and r.json()["username"] == "admin")

    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    check("错误密码被拒绝", r.status_code == 401)

    r = client.post("/api/users", headers=H,
                    json={"username": "student1", "password": "abc12345", "display_name": "学生一号"})
    check("创建普通用户", r.status_code == 200, r.text)
    r = client.post("/api/auth/login", json={"username": "student1", "password": "abc12345"})
    member_token = r.json()["token"]
    MH = {"Authorization": f"Bearer {member_token}"}
    check("普通用户登录", r.status_code == 200)

    r = client.post("/api/projects", headers=MH, json={"code": "X", "name": "x"})
    check("普通用户不能建项目(403)", r.status_code == 403)

    print("== 2. 配置管理 ==")
    r = client.get("/api/projects", headers=H)
    check("项目列表含种子数据", r.status_code == 200 and len(r.json()) >= 2)
    project_a = next(p for p in r.json() if p["code"] == "ProjectA")

    r = client.post("/api/projects", headers=H, json={"code": "ProjectC", "name": "测试项目C"})
    check("管理员创建项目", r.status_code == 200, r.text)
    project_c = r.json()

    r = client.get("/api/categories", headers=H)
    check("分类列表含种子数据", r.status_code == 200 and len(r.json()) >= 4)
    wb = next(c for c in r.json() if c["name"] == "WB")

    r = client.get(f"/api/custom-fields?category_id={wb['id']}", headers=H)
    check("WB 分类有预置字段", r.status_code == 200 and len(r.json()) >= 1, r.text)
    antibody_field = next((f for f in r.json() if f["label"] == "抗体"), None)
    check("抗体下拉字段存在", antibody_field is not None)

    r = client.post("/api/custom-fields", headers=H, json={
        "category_id": wb["id"], "label": "膜面积", "field_type": "number", "is_required": False})
    check("新增数字自定义字段", r.status_code == 200, r.text)

    r = client.post("/api/objects", headers=MH, json={"name": "H9C2细胞", "kind": "cell"})
    check("成员快速新建对象", r.status_code == 200, r.text)
    h9c2 = r.json()

    r = client.post("/api/tags", headers=H, json={"name": "预实验"})
    check("新建标签", r.status_code == 200)
    tag1 = r.json()

    print("== 3. 上传（分片 + SHA256 + 去重 + 缩略图）==")
    png = make_png()
    up1 = upload_bytes(png, "wb_gel_01.png", H)
    check("分片上传成功", "file_id" in up1, str(up1))
    check("服务端 SHA256 正确", up1["sha256"] == hashlib.sha256(png).hexdigest())

    r = client.post("/api/uploads/check-hash", headers=H, json={"sha256": up1["sha256"]})
    check("秒传查询命中", r.status_code == 200 and r.json()["exists"] is True)

    up2 = upload_bytes(png, "wb_gel_01_copy.png", H)
    check("相同内容去重", up2["dedup"] is True and up2["file_id"] == up1["file_id"])

    big = make_png(300, 200, (10, 100, 220)) + b"\0" * (6 * 1024 * 1024)  # 超过一片
    up3 = upload_bytes(big, "patho_scan.png", H)
    check("多分片文件上传", up3["sha256"] == hashlib.sha256(big).hexdigest())

    txt = "sample_id,ct\n1,24.5\n2,25.1\n".encode()
    up4 = upload_bytes(txt, "qpcr_result.csv", H)

    print("== 4. 创建数据条目 ==")
    r = client.post("/api/records", headers=H, json={
        "file_ids": [up1["file_id"]], "kind": "raw",
        "project_id": project_a["id"], "category_id": wb["id"], "object_id": h9c2["id"],
        "recorded_date": "2026-08-01", "title": "GAPDH 内参", "note": "第一批",
        "custom_values": {"抗体": "anti-GAPDH", "曝光时间": "30s"},
        "tag_ids": [tag1["id"]],
    })
    check("创建原始数据条目", r.status_code == 200 and len(r.json()["items"]) == 1, r.text)
    rec1 = r.json()["items"][0]
    check("返回 SHA256 与大小", rec1["sha256"] == up1["sha256"] and rec1["size"] == len(png))
    check("返回标签", rec1["tags"] == ["预实验"])

    r = client.post("/api/records", headers=H, json={
        "file_ids": [up1["file_id"]], "kind": "raw", "category_id": wb["id"],
        "custom_values": {"抗体": "不存在选项"},
    })
    check("下拉字段校验拒绝(422)", r.status_code == 422, r.text)

    r = client.post("/api/records", headers=H, json={
        "file_ids": [up4["file_id"]], "kind": "raw", "project_id": project_c["id"],
        "category_id": wb["id"], "custom_values": {},
    })
    rec2 = r.json()["items"][0]
    check("第二条记录创建", r.status_code == 200 and rec2["project_code"] == "ProjectC")

    print("== 5. 列表与筛选 ==")
    r = client.get("/api/records", headers=H)
    check("列表分页结构", r.status_code == 200 and r.json()["total"] == 2)
    r = client.get(f"/api/records?project_id={project_a['id']}", headers=H)
    check("按项目筛选", r.json()["total"] == 1 and r.json()["items"][0]["id"] == rec1["id"])
    r = client.get("/api/records?q=wb_gel", headers=H)
    check("关键词筛选", r.json()["total"] == 1)
    r = client.get(f"/api/records?q={up1['sha256'][:16]}", headers=H)
    check("按 SHA256 前缀搜索", r.json()["total"] == 1)
    r = client.get(f"/api/records?tag_id={tag1['id']}", headers=H)
    check("按标签筛选", r.json()["total"] == 1)
    r = client.get("/api/records?used=true", headers=H)
    check("按已用筛选（空）", r.json()["total"] == 0)

    print("== 6. 派生文件与谱系 ==")
    crop = make_png(80, 40, (200, 30, 30))
    up_crop = upload_bytes(crop, "gapdh_band_crop.png", H)
    r = client.post("/api/records", headers=H, json={
        "file_ids": [up_crop["file_id"]], "kind": "derived", "parent_record_id": rec1["id"],
        "derive_note": "GAPDH 条带截取", "title": "Fig3B 用条带",
    })
    check("创建派生条目", r.status_code == 200, r.text)
    recd = r.json()["items"][0]
    check("派生继承父项目/分类", recd["project_code"] == "ProjectA" and recd["category_name"] == "WB")

    r = client.get(f"/api/records/{rec1['id']}/lineage", headers=H)
    check("谱系树包含派生子节点", r.status_code == 200
          and r.json()["tree"]["children"][0]["id"] == recd["id"])

    print("== 7. 标记已用与保护警告 ==")
    r = client.post(f"/api/records/{recd['id']}/mark-used", headers=H,
                    json={"publication_ref": "论文X Fig.3B"})
    check("标记已用于发表", r.status_code == 200, r.text)

    r = client.get("/api/records?used=true", headers=H)
    check("已用筛选命中", r.json()["total"] == 1)

    # 父文件（原始数据）再用于另一篇论文 → 应警告
    r = client.post(f"/api/records/{rec1['id']}/mark-used", headers=H,
                    json={"publication_ref": "论文Y Fig.1A"})
    check("谱系重复使用给出警告", r.status_code == 200 and len(r.json()["warnings"]) > 0, r.text)

    # 已用父文件再派生 → 创建时警告
    up_crop2 = upload_bytes(make_png(90, 30, (30, 200, 30)), "crop2.png", H)
    r = client.post("/api/records", headers=H, json={
        "file_ids": [up_crop2["file_id"]], "kind": "derived", "parent_record_id": rec1["id"],
        "derive_note": "另一条带",
    })
    check("派生自己用父文件时警告", r.status_code == 200 and len(r.json()["warnings"]) > 0)
    recd2 = r.json()["items"][0]

    r = client.post(f"/api/records/{recd['id']}/unmark-used", headers=H)
    check("取消已用标记", r.status_code == 200)

    print("== 8. 编辑与审计 ==")
    r = client.patch(f"/api/records/{rec1['id']}", headers=H, json={"project_id": project_c["id"]})
    check("修改项目归属", r.status_code == 200 and r.json()["project_code"] == "ProjectC", r.text)

    r = client.patch(f"/api/records/{rec1['id']}", headers=H,
                     json={"custom_values": {"抗体": "anti-Tubulin"}})
    check("修改自定义字段", r.status_code == 200 and r.json()["custom_values"]["抗体"] == "anti-Tubulin")

    r = client.get(f"/api/records/{rec1['id']}/audit", headers=H)
    actions = [lg["action"] for lg in r.json()]
    check("审计含 create/update/mark_used", "create" in actions and "update" in actions
          and "mark_used" in actions, str(actions))

    print("== 9. 缩略图 / 预览 / 下载 ==")
    for _ in range(20):
        r = client.get(f"/api/records/{rec1['id']}/thumbnail", headers=H)
        if r.status_code == 200:
            break
        time.sleep(0.3)
    check("PNG 生成缩略图", r.status_code == 200 and r.headers["content-type"].startswith("image/"))

    r = client.get(f"/api/records/{rec1['id']}/preview", headers=H)
    check("PNG 在线预览", r.status_code == 200)

    r = client.get(f"/api/records/{rec1['id']}/download", headers=H)
    check("下载内容一致", r.status_code == 200 and hashlib.sha256(r.content).hexdigest() == up1["sha256"])

    print("== 10. 批量操作 / 回收站 ==")
    r = client.post("/api/records/batch", headers=H,
                    json={"ids": [rec1["id"], rec2["id"], recd["id"]], "action": "project",
                          "project_id": project_a["id"]})
    check("批量改项目", r.status_code == 200 and r.json()["affected"] == 3, r.text)

    ids = ",".join(str(x) for x in [rec1["id"], rec2["id"]])
    r = client.get(f"/api/records/batch/zip?ids={ids}", headers=H)
    check("批量打包下载 zip", r.status_code == 200 and r.headers["content-type"] == "application/zip")

    r = client.post(f"/api/records/{rec2['id']}/delete", headers=H)
    check("移入回收站", r.status_code == 200)
    r = client.get("/api/records?deleted=true", headers=H)
    check("回收站列表可见", r.json()["total"] == 1 and r.json()["items"][0]["id"] == rec2["id"])
    r = client.get("/api/records", headers=H)
    check("正常列表不含回收站", all(it["id"] != rec2["id"] for it in r.json()["items"]))
    r = client.post(f"/api/records/{rec2['id']}/restore", headers=H)
    check("从回收站恢复", r.status_code == 200)

    r = client.delete(f"/api/records/{recd['id']}", headers=MH)
    check("成员不能彻底删除(403)", r.status_code == 403)
    r = client.delete(f"/api/records/{rec1['id']}", headers=H)
    check("有派生文件时禁止彻底删除", r.status_code == 400)

    print("== 11. 统计 / 校验 / 导出 ==")
    r = client.get("/api/stats/overview", headers=H)
    check("统计概览", r.status_code == 200 and r.json()["total_records"] >= 3, r.text)
    check("分类分布", any(c["name"] == "WB" and c["count"] >= 3 for c in r.json()["by_category"]))

    r = client.post("/api/ops/verify", headers=H)
    check("启动完整性校验", r.status_code == 200 and r.json()["status"] == "running")
    for _ in range(40):
        r = client.get("/api/ops/verify", headers=H)
        if r.json().get("status") in ("done", "error"):
            break
        time.sleep(0.3)
    check("校验完成且无损坏", r.json().get("result", {}).get("mismatched") == 0
          and r.json().get("result", {}).get("missing_files") == 0, r.text)

    r = client.post("/api/ops/export", headers=H, json={"project_id": project_a["id"]})
    check("启动项目导出", r.status_code == 200)
    job_id = r.json()["id"]
    for _ in range(60):
        r = client.get("/api/ops/export", headers=H)
        job = next((j for j in r.json() if j["id"] == job_id), None)
        if job and job["status"] in ("done", "error"):
            break
        time.sleep(0.3)
    check("导出任务完成", job["status"] == "done", str(job))
    r = client.get(f"/api/ops/export/{job_id}/download", headers=H)
    check("导出 zip 可下载", r.status_code == 200 and len(r.content) > 100)

    print("== 12. 彻底删除与物理清理 ==")
    r = client.delete(f"/api/records/{recd['id']}", headers=H)
    check("删除派生条目", r.status_code == 200, r.text)
    r = client.delete(f"/api/records/{recd2['id']}", headers=H)
    check("删除第二个派生条目", r.status_code == 200, r.text)
    blob = TEST_DATA / "pool" / up1["sha256"][:2] / up1["sha256"]
    check("去重 blob 仍保留（另有引用）", blob.exists())
    r = client.delete(f"/api/records/{rec1['id']}", headers=H)
    check("删除原始条目", r.status_code == 200)
    r = client.delete(f"/api/records/{rec2['id']}", headers=H)
    check("删除后引用清零 → blob 清理", not blob.exists(), "blob 仍存在")

    print()
    print(f"===== 冒烟测试结果：{PASSED} 通过，{len(FAILED)} 失败 =====")
    if FAILED:
        for f in FAILED:
            print(f"  失败项：{f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
