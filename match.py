import re

def enrich_jobs_with_scores(jobs_list, resume_text):
    """
    100分制精细化评分算法：通过非线性加权拉开差距，区分度极高。
    """
    # 核心技术词库
    TECH_KEYWORDS = [
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust', 'sql',
        'azure', 'aws', 'gcp', 'docker', 'kubernetes', 'react', 'node.js', 'spring boot',
        'machine learning', 'ai', 'nlp', 'racket', 'solidity', 'blockchain', 'rest api',
        'microservices', 'devops', 'testing', 'distributed systems'
    ]

    def calculate_single_score(job_item, resume_text):
        resume_text = resume_text.lower()
        title = job_item.get('jobTitle', '').lower()
        description = job_item.get('jobDescription', '').lower()
        jd_text = f"{title} {description}"
        
        score = 0.0
        reasons = []

        # --- 维度 A: 技能匹配 (权重 50) ---
        # 提取JD中要求的技能
        jd_skills = {kw for kw in TECH_KEYWORDS if re.search(rf'\b{re.escape(kw)}\b', jd_text)}
        resume_skills = {kw for kw in TECH_KEYWORDS if re.search(rf'\b{re.escape(kw)}\b', resume_text)}
        
        if jd_skills:
            overlap = resume_skills.intersection(jd_skills)
            # 【精细化处理】: 使用平方比例。
            # 理由：让低匹配度(如1/5)得分极低，高匹配度(如4/5)得分极高。
            match_ratio = len(overlap) / len(jd_skills)
            skill_score = (match_ratio ** 1.5) * 50  # 使用1.5次方拉开梯度
            score += skill_score
            if overlap:
                reasons.append(f"命中关键技术: {len(overlap)}个")
        else:
            score += 25.0 # JD没写清楚时，给一半的基础分

        # --- 维度 B: 职级与年限契合度 (权重 30) ---
        # 提取JD中可能存在的年限要求（正则匹配如 "3+ years", "5 years"）
        exp_match = re.search(r'(\d+)\+?\s*(?:year|yr)', jd_text)
        jd_years_req = int(exp_match.group(1)) if exp_match else None
        
        # 判定职级关键词
        levels = {'senior': ['senior', 'staff', 'lead', 'architect'], 'junior': ['junior', 'new grad', 'entry', 'intern']}
        jd_level = 'mid'
        for lvl, kws in levels.items():
            if any(kw in title for kw in kws): # 标题的职级权重更高
                jd_level = lvl; break
        
        res_level = 'mid'
        for lvl, kws in levels.items():
            if any(kw in resume_text for kw in kws):
                res_level = lvl; break

        if jd_level == res_level:
            score += 30
            reasons.append(f"职级完美对口 ({jd_level})")
        elif jd_level == 'junior' and res_level == 'mid':
            score += 20 # 降级申请，匹配度尚可
        elif jd_level == 'senior' and res_level == 'junior':
            score -= 10 # 严重越级，不仅不加分还要倒扣，增加差距
            reasons.append("警告: 资历可能不足")
        else:
            score += 15 # 默认中等匹配

        # --- 维度 C: 核心领域与标题匹配 (权重 20) ---
        # 提取标题中的实词（排除软件、工程师等泛词）
        noise_words = {'software', 'engineer', 'developer', 'senior', 'junior', 'full', 'stack'}
        title_keywords = set(re.findall(r'\w+', title)) - noise_words
        
        title_bonus = 0
        for tk in title_keywords:
            if len(tk) > 2 and tk in resume_text:
                title_bonus += 10 # 命中一个标题核心词加10分
        
        score += min(title_bonus, 20)
        if title_bonus > 0:
            reasons.append("标题领域高度契合")

        # 最终得分取整，范围 0-100
        return max(0, min(round(score), 100)), reasons

    # 处理所有职位
    for job in jobs_list:
        match_score, match_reasons = calculate_single_score(job, user_resume_text)
        job['match_score'] = match_score
        job['match_reasons'] = match_reasons
    
    # 按照分数从高到低排序
    return sorted(jobs_list, key=lambda x: x['match_score'], reverse=True)
