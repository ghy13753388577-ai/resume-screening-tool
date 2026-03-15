import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict

import jieba


@dataclass
class MatchResult:
    """匹配结果"""
    keyword: str
    matched: bool
    match_count: int
    context: List[str]
    weight: float


@dataclass
class JobRequirements:
    """职位要求"""
    title: str = ""
    required_skills: List[str] = None
    preferred_skills: List[str] = None
    min_education: str = ""
    min_years_experience: int = 0
    required_certifications: List[str] = None
    required_companies: List[str] = None  # 硬性指标：要求的公司
    required_roles: List[str] = None      # 硬性指标：要求的职位
    bonus_skills: List[str] = None        # 加分项：技能
    bonus_certifications: List[str] = None  # 加分项：证书
    description: str = ""
    
    def __post_init__(self):
        if self.required_skills is None:
            self.required_skills = []
        if self.preferred_skills is None:
            self.preferred_skills = []
        if self.required_certifications is None:
            self.required_certifications = []
        if self.required_companies is None:
            self.required_companies = []
        if self.required_roles is None:
            self.required_roles = []
        if self.bonus_skills is None:
            self.bonus_skills = []
        if self.bonus_certifications is None:
            self.bonus_certifications = []


class KeywordMatcher:
    """关键词匹配器"""
    
    def __init__(self):
        self.skill_synonyms = {
            'python': ['python', 'py'],
            'javascript': ['javascript', 'js'],
            'typescript': ['typescript', 'ts'],
            'golang': ['golang', 'go'],
            'kubernetes': ['kubernetes', 'k8s'],
            'react': ['react', 'reactjs', 'react.js'],
            'vue': ['vue', 'vuejs', 'vue.js'],
            'node': ['node', 'nodejs', 'node.js'],
            'spring': ['spring', 'springboot', 'spring boot'],
            'aws': ['aws', 'amazon web services'],
            'azure': ['azure', 'microsoft azure'],
            'ai': ['ai', '人工智能', 'artificial intelligence'],
            'ml': ['ml', 'machine learning', '机器学习'],
            'nlp': ['nlp', '自然语言处理', 'natural language processing'],
            'cv': ['cv', '计算机视觉', 'computer vision'],
        }
        
        # 教育水平等级
        self.education_levels = {
            '高中': 1,
            '中专': 2,
            '大专': 3,
            '本科': 4,
            '学士': 4,
            '硕士': 5,
            '研究生': 5,
            'mba': 5,
            'emba': 5,
            '博士': 6,
        }
    
    def match(self, resume_data: Dict[str, Any], job_requirements: JobRequirements) -> Dict[str, Any]:
        """执行匹配并返回结果"""
        results = {
            "overall_match_score": 0.0,
            "skill_match": {},
            "education_match": {},
            "experience_match": {},
            "certification_match": {},
            "company_match": {},
            "role_match": {},
            "bonus_score": 0.0,
            "detailed_matches": [],
            "meets_hard_requirements": True
        }
        
        # 技能匹配
        skill_result = self._match_skills(resume_data.get('skills', []), job_requirements)
        results["skill_match"] = skill_result
        
        # 教育匹配
        education_result = self._match_education(resume_data.get('education', []), job_requirements)
        results["education_match"] = education_result
        if not education_result.get("meets_requirement", False):
            results["meets_hard_requirements"] = False
        
        # 经验匹配
        experience_result = self._match_experience(resume_data.get('work_experience', []), job_requirements)
        results["experience_match"] = experience_result
        if not experience_result.get("meets_requirement", False):
            results["meets_hard_requirements"] = False
        
        # 证书匹配
        cert_result = self._match_certifications(resume_data.get('certifications', []), job_requirements)
        results["certification_match"] = cert_result
        
        # 公司匹配（硬性指标）
        company_result = self._match_companies(resume_data.get('work_experience', []), job_requirements)
        results["company_match"] = company_result
        if job_requirements.required_companies and not company_result.get("matched", False):
            results["meets_hard_requirements"] = False
        
        # 职位匹配（硬性指标）
        role_result = self._match_roles(resume_data.get('work_experience', []), job_requirements)
        results["role_match"] = role_result
        if job_requirements.required_roles and not role_result.get("matched", False):
            results["meets_hard_requirements"] = False
        
        # 加分项
        bonus_score = self._calculate_bonus(resume_data, job_requirements)
        results["bonus_score"] = bonus_score
        
        # 计算总体匹配分数
        weights = {
            "skills": 0.35,
            "education": 0.2,
            "experience": 0.25,
            "certifications": 0.1,
            "company": 0.05,
            "role": 0.05
        }
        
        base_score = (
            skill_result.get("score", 0) * weights["skills"] +
            education_result.get("score", 0) * weights["education"] +
            experience_result.get("score", 0) * weights["experience"] +
            cert_result.get("score", 0) * weights["certifications"] +
            company_result.get("score", 0) * weights["company"] +
            role_result.get("score", 0) * weights["role"]
        )
        
        # 应用加分项
        overall_score = base_score + bonus_score
        overall_score = min(1.0, overall_score)
        
        results["overall_match_score"] = round(overall_score, 2)
        
        return results
    
    def _match_skills(self, resume_skills: List[str], job: JobRequirements) -> Dict[str, Any]:
        """匹配技能"""
        result = {
            "required": {"matched": [], "missing": [], "score": 0},
            "preferred": {"matched": [], "missing": [], "score": 0},
            "score": 0
        }
        
        resume_skills_lower = [s.lower() for s in resume_skills]
        
        # 匹配必需技能
        required_total = len(job.required_skills)
        required_matched = 0
        
        for skill in job.required_skills:
            skill_lower = skill.lower()
            if self._skill_matches(skill_lower, resume_skills_lower):
                result["required"]["matched"].append(skill)
                required_matched += 1
            else:
                result["required"]["missing"].append(skill)
        
        result["required"]["score"] = required_matched / required_total if required_total > 0 else 1.0
        
        # 匹配优先技能
        preferred_total = len(job.preferred_skills)
        preferred_matched = 0
        
        for skill in job.preferred_skills:
            skill_lower = skill.lower()
            if self._skill_matches(skill_lower, resume_skills_lower):
                result["preferred"]["matched"].append(skill)
                preferred_matched += 1
            else:
                result["preferred"]["missing"].append(skill)
        
        result["preferred"]["score"] = preferred_matched / preferred_total if preferred_total > 0 else 0.0
        
        # 综合技能分数 (必需技能占70%，优先技能占30%)
        result["score"] = result["required"]["score"] * 0.7 + result["preferred"]["score"] * 0.3
        result["score"] = round(result["score"], 2)
        
        return result
    
    def _skill_matches(self, target_skill: str, resume_skills: List[str]) -> bool:
        """检查技能是否匹配（考虑同义词）"""
        # 直接匹配
        if target_skill in resume_skills:
            return True
        
        # 同义词匹配
        for skill_group in self.skill_synonyms.values():
            if target_skill in skill_group:
                for synonym in skill_group:
                    if synonym in resume_skills:
                        return True
        
        # 部分匹配
        for skill in resume_skills:
            if target_skill in skill or skill in target_skill:
                return True
        
        return False
    
    def _match_education(self, resume_education: List[Dict], job: JobRequirements) -> Dict[str, Any]:
        """匹配教育背景"""
        result = {
            "candidate_level": "",
            "required_level": job.min_education,
            "meets_requirement": False,
            "score": 0
        }
        
        if not resume_education:
            return result
        
        # 获取候选人最高学历
        highest_level = 0
        highest_degree = ""
        
        for edu in resume_education:
            degree = edu.get('degree', '')
            for level_name, level_value in self.education_levels.items():
                if level_name in degree:
                    if level_value > highest_level:
                        highest_level = level_value
                        highest_degree = degree
        
        result["candidate_level"] = highest_degree
        
        # 检查是否满足要求
        required_level = self.education_levels.get(job.min_education, 0)
        result["meets_requirement"] = highest_level >= required_level
        
        # 计算分数
        if required_level > 0:
            result["score"] = min(1.0, highest_level / required_level)
        else:
            result["score"] = 1.0
        
        result["score"] = round(result["score"], 2)
        
        return result
    
    def _match_experience(self, work_experience: List[Dict], job: JobRequirements) -> Dict[str, Any]:
        """匹配工作经验"""
        result = {
            "years_of_experience": 0,
            "required_years": job.min_years_experience,
            "meets_requirement": False,
            "score": 0
        }
        
        # 计算总工作年限
        total_years = self._calculate_total_years(work_experience)
        result["years_of_experience"] = total_years
        
        # 检查是否满足要求
        result["meets_requirement"] = total_years >= job.min_years_experience
        
        # 计算分数
        if job.min_years_experience > 0:
            result["score"] = min(1.0, total_years / job.min_years_experience)
        else:
            result["score"] = 1.0
        
        result["score"] = round(result["score"], 2)
        
        return result
    
    def _calculate_total_years(self, work_experience: List[Dict]) -> float:
        """计算总工作年限"""
        total_months = 0
        
        for exp in work_experience:
            period = exp.get('period', '')
            months = self._parse_period_to_months(period)
            total_months += months
        
        return round(total_months / 12, 1)
    
    def _parse_period_to_months(self, period: str) -> int:
        """将时间段解析为月数"""
        if not period:
            return 0
        
        # 尝试匹配 "2020.01 - 2021.06" 格式
        pattern1 = re.compile(r'(\d{4})[\.\-/](\d{1,2})\s*[-~至到]\s*(\d{4})[\.\-/](\d{1,2})')
        match = pattern1.search(period)
        if match:
            start_year, start_month, end_year, end_month = map(int, match.groups())
            return (end_year - start_year) * 12 + (end_month - start_month)
        
        # 尝试匹配 "2020 - 至今" 格式
        pattern2 = re.compile(r'(\d{4})\s*[-~至到]\s*(至今|Present|现在)')
        match = pattern2.search(period)
        if match:
            start_year = int(match.group(1))
            current_year = 2024  # 可以改为动态获取当前年份
            return (current_year - start_year) * 12
        
        return 12  # 默认1年
    
    def _match_certifications(self, resume_certs: List[str], job: JobRequirements) -> Dict[str, Any]:
        """匹配证书"""
        result = {
            "matched": [],
            "missing": [],
            "score": 0
        }
        
        if not job.required_certifications:
            result["score"] = 1.0
            return result
        
        resume_certs_lower = [c.lower() for c in resume_certs]
        
        matched = 0
        for cert in job.required_certifications:
            cert_lower = cert.lower()
            if any(cert_lower in rc or rc in cert_lower for rc in resume_certs_lower):
                result["matched"].append(cert)
                matched += 1
            else:
                result["missing"].append(cert)
        
        result["score"] = matched / len(job.required_certifications)
        result["score"] = round(result["score"], 2)
        
        return result
    
    def _match_companies(self, work_experience: List[Dict], job: JobRequirements) -> Dict[str, Any]:
        """匹配公司（硬性指标）"""
        result = {
            "matched": False,
            "matched_companies": [],
            "score": 0
        }
        
        if not job.required_companies:
            result["score"] = 1.0
            return result
        
        resume_companies = [exp.get('company', '').lower() for exp in work_experience]
        
        for company in job.required_companies:
            company_lower = company.lower()
            if any(company_lower in rc or rc in company_lower for rc in resume_companies):
                result["matched"] = True
                result["matched_companies"].append(company)
                result["score"] = 1.0
                break
        
        return result
    
    def _match_roles(self, work_experience: List[Dict], job: JobRequirements) -> Dict[str, Any]:
        """匹配职位（硬性指标）"""
        result = {
            "matched": False,
            "matched_roles": [],
            "score": 0
        }
        
        if not job.required_roles:
            result["score"] = 1.0
            return result
        
        resume_roles = [exp.get('position', '').lower() for exp in work_experience]
        
        for role in job.required_roles:
            role_lower = role.lower()
            if any(role_lower in rr or rr in role_lower for rr in resume_roles):
                result["matched"] = True
                result["matched_roles"].append(role)
                result["score"] = 1.0
                break
        
        return result
    
    def _calculate_bonus(self, resume_data: Dict[str, Any], job: JobRequirements) -> float:
        """计算加分项"""
        bonus = 0.0
        
        # 技能加分
        if job.bonus_skills:
            resume_skills = [s.lower() for s in resume_data.get('skills', [])]
            matched_bonus_skills = 0
            for skill in job.bonus_skills:
                if self._skill_matches(skill.lower(), resume_skills):
                    matched_bonus_skills += 1
            if job.bonus_skills:
                bonus += (matched_bonus_skills / len(job.bonus_skills)) * 0.05
        
        # 证书加分
        if job.bonus_certifications:
            resume_certs = [c.lower() for c in resume_data.get('certifications', [])]
            matched_bonus_certs = 0
            for cert in job.bonus_certifications:
                if any(cert.lower() in rc or rc in cert.lower() for rc in resume_certs):
                    matched_bonus_certs += 1
            if job.bonus_certifications:
                bonus += (matched_bonus_certs / len(job.bonus_certifications)) * 0.03
        
        # 工作经验年限加分（超出要求的部分）
        exp_years = self._calculate_total_years(resume_data.get('work_experience', []))
        if exp_years > job.min_years_experience:
            extra_years = min(exp_years - job.min_years_experience, 5)  # 最多加5年的分
            bonus += (extra_years / 5) * 0.02
        
        return round(bonus, 3)
    
    def extract_keywords_from_job_description(self, description: str) -> JobRequirements:
        """从职位描述中提取关键词并创建职位要求"""
        job = JobRequirements(description=description)
        
        # 提取技能关键词
        for skill_group in self.skill_synonyms.values():
            for skill in skill_group:
                if skill.lower() in description.lower():
                    # 检查是否是"必需"技能（通过关键词判断）
                    if any(word in description.lower() for word in ['必须', '必需', 'required', 'must have', '必备']):
                        if skill not in job.required_skills:
                            job.required_skills.append(skill)
                    else:
                        if skill not in job.preferred_skills:
                            job.preferred_skills.append(skill)
                    break
        
        # 提取学历要求
        for edu_level in self.education_levels.keys():
            if edu_level in description:
                job.min_education = edu_level
                break
        
        # 提取经验要求
        exp_pattern = re.compile(r'(\d+)[\s]*[\+]?[\s]*年[\s]*(?:以上)?(?:工作)?经验')
        match = exp_pattern.search(description)
        if match:
            job.min_years_experience = int(match.group(1))
        
        return job
