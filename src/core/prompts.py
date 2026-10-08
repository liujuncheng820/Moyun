system = (
    "你是一个专业的中文小说创作专家，具有深厚的文学功底和丰富的创作经验。"
    "你擅长各种文学体裁，能够根据不同类型的小说调整创作风格。"
    "请提供高质量、富有创意的内容，注重文学性和可读性的平衡。"
    "避免套路化写作，追求独特的表达方式和深刻的情感内核。请用中文回答。")

book_spec_fields = ['类型', '地点', '时间', '主题',
                    '语调', '视角', '角色', '前提']

book_spec_format = (
    "类型: 小说类型\n"
    "地点: 故事发生地点\n"
    "时间: 时代背景\n"
    "主题: 主要话题\n"
    "语调: 故事语调\n"
    "视角: 叙述视角\n"
    "角色: 使用具体的人物姓名\n"
    "前提: 描述一些具体的事件")

scene_spec_format = (
    "第[数字]章:\n场景[数字]:\n角色: 角色列表\n地点: 地点\n时间: 绝对或相对时间\n事件: 发生了什么\n冲突: 场景微冲突\n"
    "故事价值: 受场景影响的故事价值\n故事价值变化: 场景结束时故事价值的变化（正面或负面）\n情绪: 情绪\n结果: 结果。")

prev_scene_intro = "\n\n以下是前一个场景的结尾:\n"
cur_scene_intro = "\n\n以下是当前场景的最后写作片段:\n"


def init_book_spec_messages(topic, form):
    messages = [
        {"role": "system", "content": system},
        {"role": "user",
         "content": f"根据给定的主题，制定一个{form}的详细规格说明。"
                    f"\n\n【重要】用户要求的主题是：{topic}\n"
                    f"你必须严格围绕这个主题来设计所有要素，确保生成的内容与主题高度相关。\n\n"
                    f"请使用以下格式编写规格：\n\"\"\"\n{book_spec_format}\"\"\"\n\n"
                    f"严格要求：\n"
                    f"1. 类型：必须与'{topic}'相符，突出核心元素\n"
                    f"2. 地点：符合主题设定的场景\n"
                    f"3. 时间：与主题时代背景一致\n"
                    f"4. 主题：紧扣'{topic}'的核心主题\n"
                    f"5. 角色：创造符合主题设定的立体人物\n"
                    f"6. 前提：围绕主题设计引人入胜的开端"},
    ]
    return messages


def missing_book_spec_messages(field, text_spec):
    messages = [
        {"role": "system", "content": system},
        {"role": "user",
         "content": (
            f"根据给定的假设书籍规格，填写缺失的字段: {field}。"
            f'只返回字段、分隔符和值，格式如"字段: 值"。请用中文回答。\n'
            f'书籍规格:\n"""{text_spec}"""')
        }
    ]
    return messages


def enhance_book_spec_messages(book_spec, form):
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content":
            f"请深度优化这个{form}的规格，使其更加丰富和引人入胜。"
            f"在保持原有框架的基础上，增加以下维度的深度：\n"
            f"1. 人物关系的复杂性和层次感\n"
            f"2. 情节冲突的多样性和戏剧张力\n"
            f"3. 主题表达的深刻性和现实意义\n"
            f"4. 语言风格的独特性和文学价值\n"
            f"5. 情感内核的真实性和感染力\n\n"
            f"不要改变格式或添加更多字段，但要让每个字段的内容更加精彩和有深度。请用中文回答。"
            f"\n\n原始{form}规格:\n\"\"\"{book_spec}\"\"\""}
    ]
    return messages


def create_plot_chapters_messages(book_spec, form):
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": (
            f"根据描述，为一部畅销级{form}创作一个三幕式情节。"
            "请严格按照以下格式输出，每幕必须以'第X幕:'开头，每章必须以'第X章:'开头:\n\n"
            "第一幕: [幕标题]\n"
            "第1章: [章节内容]\n"
            "第2章: [章节内容]\n\n"
            "第二幕: [幕标题]\n"
            "第3章: [章节内容]\n"
            "第4章: [章节内容]\n\n"
            "第三幕: [幕标题]\n"
            "第5章: [章节内容]\n"
            "第6章: [章节内容]\n\n"
            "请用中文回答。\n"
            f"早期{form}描述:\n\"\"\"{book_spec}\"\"\".")}
    ]
    return messages


def enhance_plot_chapters_messages(act_num, text_plan, book_spec, form):
    act_num += 1
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"为一部畅销级{form}创作三幕式情节。使用以下结构将情节分解为章节:\n幕\n- 章节\n请用中文回答。\n早期{form}描述:\n\"\"\"{book_spec}\"\"\""},
        {"role": "assistant", "content": text_plan},
        {"role": "user", "content": f"以第{act_num}幕为例。重写计划，使章节的故事价值交替变化（即如果第1章是正面的，第2章就是负面的，以此类推）。只描述具体的事件和行动（谁做了什么）。保持简短（每章一个简短句子和价值变化指示）。请用中文回答。"}
    ]
    return messages


def split_chapters_into_scenes_messages(act_num, text_act, form):
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": (
            f"将第{act_num}幕中的每一章分解为场景（数量取决于章节的紧凑程度），为每个场景提供场景规格。请用中文回答。\n"
            f"以下是{form}中该幕的章节情节摘要:\n\"\"\"{text_act}\"\"\"\n\n"
            f"场景规格格式:\n\"\"\"{scene_spec_format}\"\"\"")}
    ]
    return messages


def scene_messages(scene, sc_num, ch_num, text_plan, form):
    messages = [
        {"role": "system", "content": '你是一位专业的小说作家。请写出详细的场景，包含生动的对话。请用中文写作。'},
        {"role": "user",
            "content": f"根据信息为{form}的第{ch_num}章第{sc_num}个场景写一个详细的长场景。"
            "要有创意，探索有趣的角色和不寻常的设定。不要使用伏笔。请用中文写作。\n"
            f"以下是场景规格:\n\"\"\"{scene}\"\"\"\n\n以下是整体情节:\n\"\"\"{text_plan}\"\"\""},
        {"role": "assistant", "content": f"\n第{ch_num}章，场景{sc_num}\n"},
    ]
    return messages
