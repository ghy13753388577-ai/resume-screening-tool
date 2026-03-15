import os
import io
from typing import List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from resume_parser import ResumeParser, ParsedResume
from keyword_matcher import KeywordMatcher, JobRequirements
from evaluator import ResumeEvaluator, EvaluationResult


app = FastAPI(title="简历筛选工具", description="智能简历解析、关键词匹配及标准化评估系统")

# 创建上传目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 初始化组件
resume_parser = ResumeParser()
keyword_matcher = KeywordMatcher()
evaluator = ResumeEvaluator()

# 存储解析结果
parsed_resumes: Dict[str, Dict[str, Any]] = {}
job_requirements: JobRequirements = None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>简历筛选工具</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        h1 {
            text-align: center;
            color: white;
            margin-bottom: 30px;
            font-size: 2.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .card {
            background: white;
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5rem;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 600;
        }
        
        input[type="text"],
        input[type="number"],
        textarea {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        input[type="text"]:focus,
        input[type="number"]:focus,
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        textarea {
            resize: vertical;
            min-height: 120px;
        }
        
        .file-input-wrapper {
            position: relative;
            overflow: hidden;
            display: inline-block;
            width: 100%;
        }
        
        .file-input-wrapper input[type=file] {
            position: absolute;
            left: -9999px;
        }
        
        .file-input-label {
            display: block;
            padding: 40px 20px;
            border: 3px dashed #667eea;
            border-radius: 12px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: #f8f9ff;
        }
        
        .file-input-label:hover {
            background: #eef1ff;
            border-color: #764ba2;
        }
        
        .file-input-label i {
            font-size: 48px;
            color: #667eea;
            margin-bottom: 10px;
            display: block;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 32px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }
        
        .btn-secondary {
            background: #6c757d;
        }
        
        .btn-success {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }
        
        .btn-group {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .result-card {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
        }
        
        .result-card h3 {
            color: #333;
            margin-bottom: 10px;
        }
        
        .score-badge {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
        }
        
        .score-excellent { background: #d4edda; color: #155724; }
        .score-good { background: #d1ecf1; color: #0c5460; }
        .score-average { background: #fff3cd; color: #856404; }
        .score-below { background: #f8d7da; color: #721c24; }
        .score-poor { background: #f5c6cb; color: #721c24; }
        
        .skill-tag {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 12px;
            margin: 2px;
        }
        
        .skill-tag.missing {
            background: #dc3545;
        }
        
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            transition: width 0.5s ease;
        }
        
        .two-column {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        
        @media (max-width: 768px) {
            .two-column {
                grid-template-columns: 1fr;
            }
        }
        
        .list-item {
            padding: 8px 0;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .list-item:last-child {
            border-bottom: none;
        }
        
        .hidden {
            display: none;
        }
        
        #loading {
            text-align: center;
            padding: 40px;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .ranking-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .ranking-table th,
        .ranking-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .ranking-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
        }
        
        .ranking-table tr:hover {
            background: #f8f9fa;
        }
        
        .rank-number {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            font-weight: 700;
            color: white;
        }
        
        .rank-1 { background: #ffd700; }
        .rank-2 { background: #c0c0c0; }
        .rank-3 { background: #cd7f32; }
        .rank-other { background: #6c757d; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 智能简历筛选工具</h1>
        
        <!-- 职位要求设置 -->
        <div class="card">
            <h2>📋 职位要求设置</h2>
            <div class="two-column">
                <div>
                    <div class="form-group">
                        <label for="job_title">职位名称</label>
                        <input type="text" id="job_title" placeholder="例如：高级Python开发工程师">
                    </div>
                    <div class="form-group">
                        <label for="required_skills">必需技能（用逗号分隔）</label>
                        <input type="text" id="required_skills" placeholder="例如：Python, Django, MySQL">
                    </div>
                    <div class="form-group">
                        <label for="preferred_skills">优先技能（用逗号分隔）</label>
                        <input type="text" id="preferred_skills" placeholder="例如：Docker, Kubernetes, Redis">
                    </div>
                    <div class="form-group">
                        <label for="required_companies">要求公司（用逗号分隔，硬性指标）</label>
                        <input type="text" id="required_companies" placeholder="例如：腾讯, 阿里, 字节">
                    </div>
                    <div class="form-group">
                        <label for="required_roles">要求职位（用逗号分隔，硬性指标）</label>
                        <input type="text" id="required_roles" placeholder="例如：后端开发, 全栈工程师">
                    </div>
                </div>
                <div>
                    <div class="form-group">
                        <label for="min_education">最低学历要求</label>
                        <input type="text" id="min_education" placeholder="例如：本科">
                    </div>
                    <div class="form-group">
                        <label for="min_years">最低工作年限</label>
                        <input type="number" id="min_years" placeholder="例如：3" min="0">
                    </div>
                    <div class="form-group">
                        <label for="bonus_skills">加分技能（用逗号分隔）</label>
                        <input type="text" id="bonus_skills" placeholder="例如：AI, 大数据, 分布式系统">
                    </div>
                    <div class="form-group">
                        <label for="bonus_certifications">加分证书（用逗号分隔）</label>
                        <input type="text" id="bonus_certifications" placeholder="例如：PMP, AWS, CKA">
                    </div>
                    <div class="form-group">
                        <label for="job_description">职位描述</label>
                        <textarea id="job_description" placeholder="详细描述职位要求和职责..."></textarea>
                    </div>
                </div>
            </div>
            <button class="btn" onclick="saveJobRequirements()">💾 保存职位要求</button>
        </div>
        
        <!-- 简历上传 -->
        <div class="card">
            <h2>📄 简历上传</h2>
            <div class="form-group">
                <div class="file-input-wrapper">
                    <input type="file" id="resume_files" multiple accept=".pdf,.docx,.doc,.txt,.jpg,.jpeg,.png,.bmp,.tiff" onchange="handleFileSelect(this)">
                    <label for="resume_files" class="file-input-label">
                        <span style="font-size: 48px;">📁</span>
                        <div>点击或拖拽上传简历</div>
                        <div style="color: #999; font-size: 14px; margin-top: 8px;">支持 PDF, DOCX, DOC, TXT, JPG, PNG, BMP, TIFF 格式</div>
                    </label>
                </div>
            </div>
            <div id="selected_files"></div>
            <div class="btn-group" style="margin-top: 20px;">
                <button class="btn" onclick="uploadResumes()">📤 上传并解析简历</button>
                <button class="btn btn-success" onclick="evaluateAll()">🔍 开始评估匹配</button>
                <button class="btn btn-secondary" onclick="clearAll()">🗑️ 清空所有</button>
            </div>
        </div>
        
        <!-- 加载中 -->
        <div id="loading" class="hidden">
            <div class="spinner"></div>
            <p>正在处理中，请稍候...</p>
        </div>
        
        <!-- 解析结果 -->
        <div id="parse_results" class="hidden">
            <div class="card">
                <h2>📊 简历解析结果</h2>
                <div id="parse_results_content"></div>
            </div>
        </div>
        
        <!-- 简历看板 -->
        <div class="card" id="kanban_board" style="display: none;">
            <h2>📊 简历看板</h2>
            <div style="display: flex; gap: 20px; overflow-x: auto;">
                <!-- 待筛选 -->
                <div class="kanban-column" style="flex: 1; min-width: 300px; background: #f8f9fa; border-radius: 12px; padding: 15px;">
                    <h3 style="text-align: center; margin-bottom: 15px; color: #667eea;">🔍 待筛选</h3>
                    <div id="todo_column"></div>
                </div>
                <!-- 待面试 -->
                <div class="kanban-column" style="flex: 1; min-width: 300px; background: #e3f2fd; border-radius: 12px; padding: 15px;">
                    <h3 style="text-align: center; margin-bottom: 15px; color: #1976d2;">📅 待面试</h3>
                    <div id="interview_column"></div>
                </div>
                <!-- 已淘汰 -->
                <div class="kanban-column" style="flex: 1; min-width: 300px; background: #ffebee; border-radius: 12px; padding: 15px;">
                    <h3 style="text-align: center; margin-bottom: 15px; color: #d32f2f;">❌ 已淘汰</h3>
                    <div id="rejected_column"></div>
                </div>
            </div>
        </div>
        
        <!-- 评估结果 -->
        <div id="eval_results" class="hidden">
            <div class="card">
                <h2>🏆 候选人排名</h2>
                <div id="ranking_content"></div>
            </div>
            <div id="detailed_evaluations"></div>
        </div>
    </div>

    <script>
        let selectedFiles = [];
        let parsedResumes = [];
        let evaluationResults = [];
        let kanbanItems = { todo: [], interview: [], rejected: [] };
        
        function handleFileSelect(input) {
            selectedFiles = Array.from(input.files);
            displaySelectedFiles();
        }
        
        function displaySelectedFiles() {
            const container = document.getElementById('selected_files');
            if (selectedFiles.length === 0) {
                container.innerHTML = '';
                return;
            }
            
            let html = '<div style="margin-top: 15px;"><strong>已选择 ' + selectedFiles.length + ' 个文件：</strong></div>';
            html += '<div style="margin-top: 10px;">';
            selectedFiles.forEach((file, index) => {
                html += '<span style="display: inline-block; background: #e9ecef; padding: 6px 12px; margin: 4px; border-radius: 4px; font-size: 14px;">';
                html += '📄 ' + file.name;
                html += '</span>';
            });
            html += '</div>';
            container.innerHTML = html;
        }
        
        async function saveJobRequirements() {
            const data = {
                title: document.getElementById('job_title').value,
                required_skills: document.getElementById('required_skills').value,
                preferred_skills: document.getElementById('preferred_skills').value,
                required_companies: document.getElementById('required_companies').value,
                required_roles: document.getElementById('required_roles').value,
                min_education: document.getElementById('min_education').value,
                min_years: parseInt(document.getElementById('min_years').value) || 0,
                bonus_skills: document.getElementById('bonus_skills').value,
                bonus_certifications: document.getElementById('bonus_certifications').value,
                description: document.getElementById('job_description').value
            };
            
            try {
                const response = await fetch('/api/job-requirements', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                if (response.ok) {
                    alert('✅ 职位要求已保存！');
                } else {
                    alert('❌ 保存失败，请重试');
                }
            } catch (error) {
                alert('❌ 网络错误：' + error.message);
            }
        }
        
        async function uploadResumes() {
            if (selectedFiles.length === 0) {
                alert('请先选择简历文件');
                return;
            }
            
            showLoading(true);
            
            const formData = new FormData();
            selectedFiles.forEach(file => {
                formData.append('files', file);
            });
            
            try {
                const response = await fetch('/api/parse-resumes', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                parsedResumes = result.resumes || [];
                displayParseResults();
            } catch (error) {
                alert('❌ 上传失败：' + error.message);
            } finally {
                showLoading(false);
            }
        }
        
        function displayParseResults() {
            const container = document.getElementById('parse_results');
            const content = document.getElementById('parse_results_content');
            
            if (parsedResumes.length === 0) {
                content.innerHTML = '<p>暂无解析结果</p>';
                container.classList.remove('hidden');
                return;
            }
            
            let html = '';
            parsedResumes.forEach((resume, index) => {
                html += '<div class="result-card">';
                html += '<h3>👤 ' + (resume.name || '未识别姓名') + '</h3>';
                html += '<div style="color: #666; margin-bottom: 10px;">';
                html += resume.email ? '📧 ' + resume.email + ' ' : '';
                html += resume.phone ? '📱 ' + resume.phone : '';
                html += '</div>';
                
                if (resume.skills && resume.skills.length > 0) {
                    html += '<div style="margin: 10px 0;">';
                    html += '<strong>技能：</strong>';
                    resume.skills.forEach(skill => {
                        html += '<span class="skill-tag">' + skill + '</span>';
                    });
                    html += '</div>';
                }
                
                if (resume.education && resume.education.length > 0) {
                    html += '<div style="margin: 10px 0;">';
                    html += '<strong>教育背景：</strong>';
                    resume.education.forEach(edu => {
                        html += '<div class="list-item">';
                        html += (edu.school || '') + ' ' + (edu.degree || '') + ' ' + (edu.major || '');
                        html += '</div>';
                    });
                    html += '</div>';
                }
                
                if (resume.work_experience && resume.work_experience.length > 0) {
                    html += '<div style="margin: 10px 0;">';
                    html += '<strong>工作经历：</strong>';
                    resume.work_experience.forEach(exp => {
                        html += '<div class="list-item">';
                        html += (exp.company || '') + ' - ' + (exp.position || '');
                        html += '</div>';
                    });
                    html += '</div>';
                }
                
                html += '</div>';
            });
            
            content.innerHTML = html;
            container.classList.remove('hidden');
        }
        
        async function evaluateAll() {
            if (parsedResumes.length === 0) {
                alert('请先上传并解析简历');
                return;
            }
            
            showLoading(true);
            
            try {
                const response = await fetch('/api/evaluate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ resumes: parsedResumes })
                });
                
                const result = await response.json();
                evaluationResults = result.evaluations || [];
                displayEvaluationResults();
            } catch (error) {
                alert('❌ 评估失败：' + error.message);
            } finally {
                showLoading(false);
            }
        }
        
        function displayEvaluationResults() {
            const container = document.getElementById('eval_results');
            const rankingContent = document.getElementById('ranking_content');
            const detailedContent = document.getElementById('detailed_evaluations');
            
            // 显示排名
            let rankingHtml = '<table class="ranking-table">';
            rankingHtml += '<tr><th>排名</th><th>候选人</th><th>综合得分</th><th>评级</th><th>优势</th></tr>';
            
            evaluationResults.forEach((eval, index) => {
                const rankClass = index === 0 ? 'rank-1' : index === 1 ? 'rank-2' : index === 2 ? 'rank-3' : 'rank-other';
                rankingHtml += '<tr>';
                rankingHtml += '<td><span class="rank-number ' + rankClass + '">' + (index + 1) + '</span></td>';
                rankingHtml += '<td><strong>' + eval.candidate_name + '</strong></td>';
                rankingHtml += '<td><strong>' + (eval.overall_score * 100).toFixed(1) + '%</strong></td>';
                rankingHtml += '<td><span class="score-badge ' + getScoreClass(eval.overall_score) + '">' + eval.overall_level + '</span></td>';
                rankingHtml += '<td>' + (eval.strengths ? eval.strengths.slice(0, 2).join('、') : '') + '</td>';
                rankingHtml += '</tr>';
            });
            rankingHtml += '</table>';
            rankingContent.innerHTML = rankingHtml;
            
            // 显示详细评估
            let detailedHtml = '';
            evaluationResults.forEach((eval, index) => {
                detailedHtml += '<div class="card">';
                detailedHtml += '<h2>📋 ' + eval.candidate_name + ' - 详细评估报告</h2>';
                
                // 总体评分
                detailedHtml += '<div style="margin-bottom: 20px;">';
                detailedHtml += '<div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">';
                detailedHtml += '<span style="font-size: 18px; font-weight: 600;">综合得分：</span>';
                detailedHtml += '<span style="font-size: 32px; font-weight: 700; color: #667eea;">' + (eval.overall_score * 100).toFixed(1) + '%</span>';
                detailedHtml += '<span class="score-badge ' + getScoreClass(eval.overall_score) + '" style="font-size: 16px;">' + eval.overall_level + '</span>';
                detailedHtml += '</div>';
                detailedHtml += '<div class="progress-bar">';
                detailedHtml += '<div class="progress-fill" style="width: ' + (eval.overall_score * 100) + '%;"></div>';
                detailedHtml += '</div>';
                detailedHtml += '</div>';
                
                // 各维度评分
                if (eval.dimension_scores && eval.dimension_scores.length > 0) {
                    detailedHtml += '<h3 style="margin: 20px 0 15px; color: #555;">各维度评分</h3>';
                    detailedHtml += '<div class="two-column">';
                    eval.dimension_scores.forEach(ds => {
                        detailedHtml += '<div class="result-card">';
                        detailedHtml += '<div style="display: flex; justify-content: space-between; align-items: center;">';
                        detailedHtml += '<strong>' + ds.dimension + '</strong>';
                        detailedHtml += '<span class="score-badge ' + getScoreClass(ds.score) + '">' + (ds.score * 100).toFixed(0) + '%</span>';
                        detailedHtml += '</div>';
                        detailedHtml += '<div class="progress-bar" style="height: 8px; margin: 8px 0;">';
                        detailedHtml += '<div class="progress-fill" style="width: ' + (ds.score * 100) + '%;"></div>';
                        detailedHtml += '</div>';
                        if (ds.comments && ds.comments.length > 0) {
                            detailedHtml += '<div style="font-size: 13px; color: #666;">';
                            ds.comments.forEach(comment => {
                                detailedHtml += '<div>• ' + comment + '</div>';
                            });
                            detailedHtml += '</div>';
                        }
                        detailedHtml += '</div>';
                    });
                    detailedHtml += '</div>';
                }
                
                // 优势与劣势
                detailedHtml += '<div class="two-column" style="margin-top: 20px;">';
                
                detailedHtml += '<div>';
                detailedHtml += '<h3 style="color: #28a745; margin-bottom: 10px;">✅ 优势</h3>';
                if (eval.strengths && eval.strengths.length > 0) {
                    eval.strengths.forEach(strength => {
                        detailedHtml += '<div class="list-item">' + strength + '</div>';
                    });
                } else {
                    detailedHtml += '<div style="color: #999;">暂无特别突出的优势</div>';
                }
                detailedHtml += '</div>';
                
                detailedHtml += '<div>';
                detailedHtml += '<h3 style="color: #dc3545; margin-bottom: 10px;">⚠️ 待提升</h3>';
                if (eval.weaknesses && eval.weaknesses.length > 0) {
                    eval.weaknesses.forEach(weakness => {
                        detailedHtml += '<div class="list-item">' + weakness + '</div>';
                    });
                } else {
                    detailedHtml += '<div style="color: #999;">暂无明显的不足</div>';
                }
                detailedHtml += '</div>';
                
                detailedHtml += '</div>';
                
                // 建议
                if (eval.recommendations && eval.recommendations.length > 0) {
                    detailedHtml += '<div style="margin-top: 20px;">';
                    detailedHtml += '<h3 style="color: #667eea; margin-bottom: 10px;">💡 建议</h3>';
                    eval.recommendations.forEach(rec => {
                        detailedHtml += '<div class="list-item">' + rec + '</div>';
                    });
                    detailedHtml += '</div>';
                }
                
                detailedHtml += '</div>';
            });
            
            detailedContent.innerHTML = detailedHtml;
            container.classList.remove('hidden');
        }
        
        function getScoreClass(score) {
            if (score >= 0.85) return 'score-excellent';
            if (score >= 0.70) return 'score-good';
            if (score >= 0.55) return 'score-average';
            if (score >= 0.40) return 'score-below';
            return 'score-poor';
        }
        
        function showLoading(show) {
            const loading = document.getElementById('loading');
            if (show) {
                loading.classList.remove('hidden');
            } else {
                loading.classList.add('hidden');
            }
        }
        
        function clearAll() {
            selectedFiles = [];
            parsedResumes = [];
            evaluationResults = [];
            kanbanItems = { todo: [], interview: [], rejected: [] };
            document.getElementById('resume_files').value = '';
            document.getElementById('selected_files').innerHTML = '';
            document.getElementById('parse_results').classList.add('hidden');
            document.getElementById('eval_results').classList.add('hidden');
            document.getElementById('kanban_board').style.display = 'none';
        }
        
        function generateKanban() {
            // 清空看板
            kanbanItems = { todo: [], interview: [], rejected: [] };
            
            // 根据评估结果分配到不同状态
            evaluationResults.forEach(eval => {
                const item = {
                    id: eval.candidate_name,
                    name: eval.candidate_name,
                    score: eval.overall_score,
                    level: eval.overall_level,
                    email: parsedResumes.find(r => r.name === eval.candidate_name)?.email || '',
                    phone: parsedResumes.find(r => r.name === eval.candidate_name)?.phone || '',
                    meetsRequirements: eval.match_details?.meets_hard_requirements || false
                };
                
                if (!item.meetsRequirements) {
                    kanbanItems.rejected.push(item);
                } else if (item.score >= 0.7) {
                    kanbanItems.interview.push(item);
                } else {
                    kanbanItems.todo.push(item);
                }
            });
            
            // 显示看板
            document.getElementById('kanban_board').style.display = 'block';
            updateKanbanDisplay();
        }
        
        function updateKanbanDisplay() {
            // 更新待筛选列
            document.getElementById('todo_column').innerHTML = renderKanbanItems(kanbanItems.todo, 'todo');
            // 更新待面试列
            document.getElementById('interview_column').innerHTML = renderKanbanItems(kanbanItems.interview, 'interview');
            // 更新已淘汰列
            document.getElementById('rejected_column').innerHTML = renderKanbanItems(kanbanItems.rejected, 'rejected');
        }
        
        function renderKanbanItems(items, column) {
            if (items.length === 0) {
                return '<div style="text-align: center; color: #999; padding: 20px;">暂无数据</div>';
            }
            
            let html = '';
            items.forEach(item => {
                const scoreClass = getScoreClass(item.score);
                html += '<div style="background: white; border-radius: 8px; padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">';
                html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">';
                html += '<h4 style="margin: 0;">' + item.name + '</h4>';
                html += '<span class="score-badge ' + scoreClass + '">' + (item.score * 100).toFixed(0) + '%</span>';
                html += '</div>';
                if (item.email) {
                    html += '<div style="font-size: 13px; color: #666; margin-bottom: 5px;">📧 ' + item.email + '</div>';
                }
                if (item.phone) {
                    html += '<div style="font-size: 13px; color: #666; margin-bottom: 10px;">📱 ' + item.phone + '</div>';
                }
                html += '<div style="display: flex; gap: 8px; margin-top: 10px;">';
                
                if (column !== 'interview') {
                    html += '<button class="btn" style="font-size: 12px; padding: 6px 12px;" onclick="moveToInterview(\'' + item.id + '\')">安排面试</button>';
                }
                if (column !== 'rejected') {
                    html += '<button class="btn btn-secondary" style="font-size: 12px; padding: 6px 12px;" onclick="moveToRejected(\'' + item.id + '\')">淘汰</button>';
                }
                if (item.email) {
                    html += '<button class="btn btn-success" style="font-size: 12px; padding: 6px 12px;" onclick="sendEmail(\'' + item.email + '\', \'' + item.name + '\', \'' + column + '\')">发送通知</button>';
                }
                
                html += '</div>';
                html += '</div>';
            });
            return html;
        }
        
        function moveToInterview(id) {
            // 从原列移除
            for (const column in kanbanItems) {
                const index = kanbanItems[column].findIndex(item => item.id === id);
                if (index !== -1) {
                    const item = kanbanItems[column].splice(index, 1)[0];
                    kanbanItems.interview.push(item);
                    break;
                }
            }
            updateKanbanDisplay();
        }
        
        function moveToRejected(id) {
            // 从原列移除
            for (const column in kanbanItems) {
                const index = kanbanItems[column].findIndex(item => item.id === id);
                if (index !== -1) {
                    const item = kanbanItems[column].splice(index, 1)[0];
                    kanbanItems.rejected.push(item);
                    break;
                }
            }
            updateKanbanDisplay();
        }
        
        function sendEmail(email, name, status) {
            // 这里只是模拟发送邮件，实际项目中需要集成邮件服务
            let subject = '';
            let content = '';
            
            if (status === 'interview') {
                subject = '面试邀请 - ' + name;
                content = `亲爱的 ${name}：\n\n恭喜您通过了我们的初步筛选，我们邀请您参加面试。\n\n面试时间：请提供您的可用时间\n面试地点：线上视频面试\n\n期待与您见面！`;
            } else if (status === 'rejected') {
                subject = '感谢您的申请 - ' + name;
                content = `亲爱的 ${name}：\n\n感谢您对我们公司的关注和申请。\n\n经过仔细评估，我们认为您目前可能不是最适合该职位的人选。\n\n我们会将您的简历保存在我们的人才库中，如有合适的机会会再次与您联系。\n\n祝您职业发展顺利！`;
            } else {
                subject = '简历筛选通知 - ' + name;
                content = `亲爱的 ${name}：\n\n我们已收到您的简历，正在进行筛选。\n\n如有进一步安排，我们会及时与您联系。\n\n感谢您的耐心等待！`;
            }
            
            alert(`邮件已发送至 ${email}\n\n主题：${subject}\n\n内容：${content}`);
        }
        
        async function evaluateAll() {
            if (parsedResumes.length === 0) {
                alert('请先上传并解析简历');
                return;
            }
            
            showLoading(true);
            
            try {
                const response = await fetch('/api/evaluate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ resumes: parsedResumes })
                });
                
                const result = await response.json();
                evaluationResults = result.evaluations || [];
                displayEvaluationResults();
                generateKanban(); // 生成看板
            } catch (error) {
                alert('❌ 评估失败：' + error.message);
            } finally {
                showLoading(false);
            }
        }
    </script>
</body>
</html>
    """
    return html_content


@app.post("/api/job-requirements")
async def set_job_requirements(data: Dict[str, Any]):
    """设置职位要求"""
    global job_requirements
    
    job_requirements = JobRequirements(
        title=data.get('title', ''),
        required_skills=[s.strip() for s in data.get('required_skills', '').split(',') if s.strip()],
        preferred_skills=[s.strip() for s in data.get('preferred_skills', '').split(',') if s.strip()],
        required_companies=[s.strip() for s in data.get('required_companies', '').split(',') if s.strip()],
        required_roles=[s.strip() for s in data.get('required_roles', '').split(',') if s.strip()],
        min_education=data.get('min_education', ''),
        min_years_experience=data.get('min_years', 0),
        bonus_skills=[s.strip() for s in data.get('bonus_skills', '').split(',') if s.strip()],
        bonus_certifications=[s.strip() for s in data.get('bonus_certifications', '').split(',') if s.strip()],
        description=data.get('description', '')
    )
    
    return {"status": "success", "message": "职位要求已保存"}


@app.post("/api/parse-resumes")
async def parse_resumes(files: List[UploadFile] = File(...)):
    """解析简历"""
    global parsed_resumes
    parsed_resumes = {}
    
    results = []
    
    for file in files:
        try:
            # 读取文件内容
            content = await file.read()
            
            # 获取文件扩展名
            file_ext = Path(file.filename).suffix
            
            # 解析简历
            parsed = resume_parser.parse(content, file_ext)
            
            # 保存结果
            resume_id = file.filename
            parsed_resumes[resume_id] = parsed.to_dict()
            
            results.append(parsed.to_dict())
            
        except Exception as e:
            results.append({
                "error": f"解析失败: {str(e)}",
                "filename": file.filename
            })
    
    return {"status": "success", "resumes": results}


@app.post("/api/evaluate")
async def evaluate_resumes(data: Dict[str, Any]):
    """评估简历"""
    global job_requirements
    
    if job_requirements is None:
        # 使用默认的职位要求
        job_requirements = JobRequirements(
            title="软件工程师",
            required_skills=["Python"],
            preferred_skills=["Docker", "Kubernetes"],
            min_education="本科",
            min_years_experience=2
        )
    
    resumes = data.get('resumes', [])
    evaluations = []
    
    for resume in resumes:
        try:
            # 执行关键词匹配
            match_results = keyword_matcher.match(resume, job_requirements)
            
            # 执行标准化评估
            eval_result = evaluator.evaluate(resume, match_results)
            
            evaluations.append(eval_result.to_dict())
            
        except Exception as e:
            evaluations.append({
                "candidate_name": resume.get('name', '未知'),
                "error": str(e)
            })
    
    # 排序
    evaluations.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
    
    return {"status": "success", "evaluations": evaluations}


@app.get("/api/job-requirements")
async def get_job_requirements():
    """获取当前职位要求"""
    global job_requirements
    
    if job_requirements is None:
        return {"status": "error", "message": "未设置职位要求"}
    
    return {
        "status": "success",
        "requirements": {
            "title": job_requirements.title,
            "required_skills": job_requirements.required_skills,
            "preferred_skills": job_requirements.preferred_skills,
            "min_education": job_requirements.min_education,
            "min_years_experience": job_requirements.min_years_experience,
            "description": job_requirements.description
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
