from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum


class EvaluationLevel(Enum):
    """评估等级"""
    EXCELLENT = "优秀"
    GOOD = "良好"
    AVERAGE = "一般"
    BELOW_AVERAGE = "较差"
    POOR = "不符合"


@dataclass
class DimensionScore:
    """维度评分"""
    dimension: str
    score: float
    weight: float
    weighted_score: float
    level: EvaluationLevel
    comments: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """评估结果"""
    candidate_name: str = ""
    overall_score: float = 0.0
    overall_level: EvaluationLevel = EvaluationLevel.POOR
    dimension_scores: List[DimensionScore] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    match_details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_name": self.candidate_name,
            "overall_score": self.overall_score,
            "overall_level": self.overall_level.value,
            "dimension_scores": [
                {
                    "dimension": ds.dimension,
                    "score": ds.score,
                    "weight": ds.weight,
                    "weighted_score": ds.weighted_score,
                    "level": ds.level.value,
                    "comments": ds.comments
                }
                for ds in self.dimension_scores
            ],
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
            "match_details": self.match_details
        }


class ResumeEvaluator:
    """简历标准化评估器"""
    
    def __init__(self):
        self.dimension_weights = {
            "skills": 0.35,
            "experience": 0.30,
            "education": 0.15,
            "certifications": 0.10,
            "completeness": 0.10
        }
        
        self.level_thresholds = {
            EvaluationLevel.EXCELLENT: 0.85,
            EvaluationLevel.GOOD: 0.70,
            EvaluationLevel.AVERAGE: 0.55,
            EvaluationLevel.BELOW_AVERAGE: 0.40,
            EvaluationLevel.POOR: 0.0
        }
    
    def evaluate(self, resume_data: Dict[str, Any], match_results: Dict[str, Any]) -> EvaluationResult:
        """执行标准化评估"""
        result = EvaluationResult()
        result.candidate_name = resume_data.get('name', '未知')
        result.match_details = match_results
        
        # 计算各维度分数
        dimension_scores = []
        
        # 1. 技能匹配度评分
        skill_score = self._evaluate_skills(match_results.get('skill_match', {}))
        skill_dim = DimensionScore(
            dimension="技能匹配度",
            score=skill_score['score'],
            weight=self.dimension_weights['skills'],
            weighted_score=skill_score['score'] * self.dimension_weights['skills'],
            level=self._get_level(skill_score['score']),
            comments=skill_score['comments']
        )
        dimension_scores.append(skill_dim)
        
        # 2. 经验匹配度评分
        exp_score = self._evaluate_experience(match_results.get('experience_match', {}), resume_data.get('work_experience', []))
        exp_dim = DimensionScore(
            dimension="经验匹配度",
            score=exp_score['score'],
            weight=self.dimension_weights['experience'],
            weighted_score=exp_score['score'] * self.dimension_weights['experience'],
            level=self._get_level(exp_score['score']),
            comments=exp_score['comments']
        )
        dimension_scores.append(exp_dim)
        
        # 3. 教育背景评分
        edu_score = self._evaluate_education(match_results.get('education_match', {}))
        edu_dim = DimensionScore(
            dimension="教育背景",
            score=edu_score['score'],
            weight=self.dimension_weights['education'],
            weighted_score=edu_score['score'] * self.dimension_weights['education'],
            level=self._get_level(edu_score['score']),
            comments=edu_score['comments']
        )
        dimension_scores.append(edu_dim)
        
        # 4. 证书资质评分
        cert_score = self._evaluate_certifications(match_results.get('certification_match', {}))
        cert_dim = DimensionScore(
            dimension="证书资质",
            score=cert_score['score'],
            weight=self.dimension_weights['certifications'],
            weighted_score=cert_score['score'] * self.dimension_weights['certifications'],
            level=self._get_level(cert_score['score']),
            comments=cert_score['comments']
        )
        dimension_scores.append(cert_dim)
        
        # 5. 公司背景评分
        company_score = self._evaluate_companies(match_results.get('company_match', {}))
        company_dim = DimensionScore(
            dimension="公司背景",
            score=company_score['score'],
            weight=0.05,
            weighted_score=company_score['score'] * 0.05,
            level=self._get_level(company_score['score']),
            comments=company_score['comments']
        )
        dimension_scores.append(company_dim)
        
        # 6. 职位匹配评分
        role_score = self._evaluate_roles(match_results.get('role_match', {}))
        role_dim = DimensionScore(
            dimension="职位匹配",
            score=role_score['score'],
            weight=0.05,
            weighted_score=role_score['score'] * 0.05,
            level=self._get_level(role_score['score']),
            comments=role_score['comments']
        )
        dimension_scores.append(role_dim)
        
        # 7. 简历完整度评分
        complete_score = self._evaluate_completeness(resume_data)
        complete_dim = DimensionScore(
            dimension="简历完整度",
            score=complete_score['score'],
            weight=self.dimension_weights['completeness'],
            weighted_score=complete_score['score'] * self.dimension_weights['completeness'],
            level=self._get_level(complete_score['score']),
            comments=complete_score['comments']
        )
        dimension_scores.append(complete_dim)
        
        result.dimension_scores = dimension_scores
        
        # 计算总体分数
        result.overall_score = sum(ds.weighted_score for ds in dimension_scores)
        result.overall_score = round(result.overall_score, 2)
        result.overall_level = self._get_level(result.overall_score)
        
        # 生成优劣势分析
        result.strengths = self._identify_strengths(dimension_scores, resume_data, match_results)
        result.weaknesses = self._identify_weaknesses(dimension_scores, resume_data, match_results)
        
        # 生成建议
        result.recommendations = self._generate_recommendations(result)
        
        return result
    
    def _evaluate_skills(self, skill_match: Dict[str, Any]) -> Dict[str, Any]:
        """评估技能匹配度"""
        score = skill_match.get('score', 0)
        comments = []
        
        required = skill_match.get('required', {})
        preferred = skill_match.get('preferred', {})
        
        matched_required = len(required.get('matched', []))
        total_required = matched_required + len(required.get('missing', []))
        
        matched_preferred = len(preferred.get('matched', []))
        total_preferred = matched_preferred + len(preferred.get('missing', []))
        
        if total_required > 0:
            comments.append(f"必需技能匹配: {matched_required}/{total_required}")
        if total_preferred > 0:
            comments.append(f"优先技能匹配: {matched_preferred}/{total_preferred}")
        
        if score >= 0.8:
            comments.append("技能匹配度优秀")
        elif score >= 0.6:
            comments.append("技能匹配度良好")
        else:
            comments.append("技能匹配度有待提升")
        
        return {"score": score, "comments": comments}
    
    def _evaluate_experience(self, exp_match: Dict[str, Any], work_exp: List[Dict]) -> Dict[str, Any]:
        """评估经验匹配度"""
        score = exp_match.get('score', 0)
        years = exp_match.get('years_of_experience', 0)
        required_years = exp_match.get('required_years', 0)
        comments = []
        
        comments.append(f"工作年限: {years}年")
        if required_years > 0:
            comments.append(f"要求年限: {required_years}年")
        
        if work_exp:
            companies = [exp.get('company', '') for exp in work_exp if exp.get('company')]
            if companies:
                comments.append(f"工作经历: {', '.join(companies[:3])}")
        
        if score >= 1.0:
            comments.append("经验完全满足要求")
        elif score >= 0.8:
            comments.append("经验较为丰富")
        elif score >= 0.5:
            comments.append("经验基本匹配")
        else:
            comments.append("经验可能不足")
        
        return {"score": score, "comments": comments}
    
    def _evaluate_education(self, edu_match: Dict[str, Any]) -> Dict[str, Any]:
        """评估教育背景"""
        score = edu_match.get('score', 0)
        candidate_level = edu_match.get('candidate_level', '')
        required_level = edu_match.get('required_level', '')
        meets = edu_match.get('meets_requirement', False)
        comments = []
        
        if candidate_level:
            comments.append(f"最高学历: {candidate_level}")
        if required_level:
            comments.append(f"要求学历: {required_level}")
        
        if meets:
            comments.append("学历符合要求")
        else:
            comments.append("学历可能不符合要求")
        
        return {"score": score, "comments": comments}
    
    def _evaluate_certifications(self, cert_match: Dict[str, Any]) -> Dict[str, Any]:
        """评估证书资质"""
        score = cert_match.get('score', 0)
        matched = cert_match.get('matched', [])
        missing = cert_match.get('missing', [])
        comments = []
        
        if matched:
            comments.append(f"持有证书: {', '.join(matched)}")
        if missing:
            comments.append(f"缺少证书: {', '.join(missing)}")
        
        if not matched and not missing:
            comments.append("无特定证书要求")
        
        return {"score": score, "comments": comments}
    
    def _evaluate_completeness(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估简历完整度"""
        fields = {
            'name': '姓名',
            'email': '邮箱',
            'phone': '电话',
            'education': '教育背景',
            'work_experience': '工作经历',
            'skills': '技能',
            'projects': '项目经验'
        }
        
        filled_fields = 0
        missing_fields = []
        comments = []
        
        for field, name in fields.items():
            value = resume_data.get(field)
            if value and (not isinstance(value, list) or len(value) > 0):
                filled_fields += 1
            else:
                missing_fields.append(name)
        
        score = filled_fields / len(fields)
        
        comments.append(f"信息完整度: {filled_fields}/{len(fields)}")
        if missing_fields:
            comments.append(f"缺失信息: {', '.join(missing_fields)}")
        
        return {"score": score, "comments": comments}
    
    def _evaluate_companies(self, company_match: Dict[str, Any]) -> Dict[str, Any]:
        """评估公司背景"""
        score = company_match.get('score', 0)
        matched = company_match.get('matched', False)
        matched_companies = company_match.get('matched_companies', [])
        comments = []
        
        if matched_companies:
            comments.append(f"匹配的公司: {', '.join(matched_companies)}")
        elif score < 1.0:
            comments.append("未匹配到目标公司")
        else:
            comments.append("无特定公司要求")
        
        return {"score": score, "comments": comments}
    
    def _evaluate_roles(self, role_match: Dict[str, Any]) -> Dict[str, Any]:
        """评估职位匹配"""
        score = role_match.get('score', 0)
        matched = role_match.get('matched', False)
        matched_roles = role_match.get('matched_roles', [])
        comments = []
        
        if matched_roles:
            comments.append(f"匹配的职位: {', '.join(matched_roles)}")
        elif score < 1.0:
            comments.append("未匹配到目标职位")
        else:
            comments.append("无特定职位要求")
        
        return {"score": score, "comments": comments}
    
    def _get_level(self, score: float) -> EvaluationLevel:
        """根据分数获取等级"""
        for level, threshold in sorted(self.level_thresholds.items(), key=lambda x: x[1], reverse=True):
            if score >= threshold:
                return level
        return EvaluationLevel.POOR
    
    def _identify_strengths(self, dimension_scores: List[DimensionScore], 
                           resume_data: Dict[str, Any], 
                           match_results: Dict[str, Any]) -> List[str]:
        """识别优势"""
        strengths = []
        
        for ds in dimension_scores:
            if ds.score >= 0.8:
                strengths.append(f"{ds.dimension}表现优秀")
        
        # 技能优势
        skill_match = match_results.get('skill_match', {})
        required_matched = skill_match.get('required', {}).get('matched', [])
        if len(required_matched) >= 3:
            strengths.append(f"掌握核心技能: {', '.join(required_matched[:3])}")
        
        # 经验优势
        work_exp = resume_data.get('work_experience', [])
        if len(work_exp) >= 3:
            strengths.append(f"具有{len(work_exp)}段工作经历，经验丰富")
        
        # 教育优势
        education = resume_data.get('education', [])
        if education:
            for edu in education:
                if '硕士' in edu.get('degree', '') or '博士' in edu.get('degree', ''):
                    strengths.append("具有研究生学历")
                    break
        
        return strengths[:5]  # 最多返回5个优势
    
    def _identify_weaknesses(self, dimension_scores: List[DimensionScore],
                            resume_data: Dict[str, Any],
                            match_results: Dict[str, Any]) -> List[str]:
        """识别劣势"""
        weaknesses = []
        
        for ds in dimension_scores:
            if ds.score < 0.5:
                weaknesses.append(f"{ds.dimension}需要提升")
        
        # 技能劣势
        skill_match = match_results.get('skill_match', {})
        required_missing = skill_match.get('required', {}).get('missing', [])
        if required_missing:
            weaknesses.append(f"缺少必需技能: {', '.join(required_missing[:3])}")
        
        # 经验劣势
        exp_match = match_results.get('experience_match', {})
        if not exp_match.get('meets_requirement', True):
            weaknesses.append("工作经验可能不足")
        
        # 教育劣势
        edu_match = match_results.get('education_match', {})
        if not edu_match.get('meets_requirement', True):
            weaknesses.append("学历可能不符合要求")
        
        # 完整性劣势
        if not resume_data.get('email') or not resume_data.get('phone'):
            weaknesses.append("联系方式不完整")
        
        return weaknesses[:5]  # 最多返回5个劣势
    
    def _generate_recommendations(self, result: EvaluationResult) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if result.overall_level == EvaluationLevel.EXCELLENT:
            recommendations.append("强烈推荐面试")
            recommendations.append("候选人匹配度很高，建议优先安排")
        elif result.overall_level == EvaluationLevel.GOOD:
            recommendations.append("推荐面试")
            recommendations.append("候选人基本符合要求，建议安排面试进一步了解")
        elif result.overall_level == EvaluationLevel.AVERAGE:
            recommendations.append("可考虑面试")
            recommendations.append("候选人部分符合要求，建议根据其他候选人情况决定")
        elif result.overall_level == EvaluationLevel.BELOW_AVERAGE:
            recommendations.append("谨慎考虑")
            recommendations.append("候选人与要求有一定差距，建议优先选择其他候选人")
        else:
            recommendations.append("不推荐")
            recommendations.append("候选人与职位要求差距较大")
        
        # 根据具体维度给出建议
        for ds in result.dimension_scores:
            if ds.score < 0.5:
                recommendations.append(f"建议关注{ds.dimension}方面的提升")
        
        return recommendations[:5]
    
    def batch_evaluate(self, resumes_data: List[Dict[str, Any]], 
                      match_results_list: List[Dict[str, Any]]) -> List[EvaluationResult]:
        """批量评估"""
        results = []
        for resume, match in zip(resumes_data, match_results_list):
            result = self.evaluate(resume, match)
            results.append(result)
        return results
    
    def rank_candidates(self, evaluation_results: List[EvaluationResult]) -> List[Dict[str, Any]]:
        """对候选人进行排名"""
        ranked = []
        for result in evaluation_results:
            ranked.append({
                "name": result.candidate_name,
                "overall_score": result.overall_score,
                "level": result.overall_level.value,
                "strengths_count": len(result.strengths),
                "weaknesses_count": len(result.weaknesses)
            })
        
        # 按总体分数排序
        ranked.sort(key=lambda x: x["overall_score"], reverse=True)
        
        # 添加排名
        for i, item in enumerate(ranked, 1):
            item["rank"] = i
        
        return ranked
