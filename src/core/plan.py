"""Unifies all plot forms such as by-chapter and by-scene outlines in a single dict."""
import re
import json


class Plan:
    @staticmethod
    def split_by_act(original_plan):
        # 首先尝试按照中文格式分割 - 修复正则表达式
        # 匹配 "第一幕:", "第二幕:", "第三幕:" 等格式
        acts = re.split(r'第[一二三]幕[:：]', original_plan)
        
        # 如果成功分割出4个部分（第一个通常是空的或标题）
        if len(acts) >= 4:
            acts = acts[1:4]  # 取前三幕
        elif len(acts) == 3 and acts[0].strip() == '':
            acts = acts[1:]  # 去掉空的第一个元素
        elif len(acts) == 3:
            # 如果正好3个部分，检查第一个是否包含有效内容
            if len(acts[0].strip()) < 10:  # 第一个部分很短，可能是标题
                acts = acts[1:] if len(acts) > 1 else acts
        else:
            # 备用方案：按照英文格式分割
            acts = re.split('\n.{0,5}?Act ', original_plan)
            # remove random short garbage from re split
            acts = [text.strip() for text in acts[:]
                    if (text and (len(text.split()) > 3))]
            if len(acts) == 4:
                acts = acts[1:]
            elif len(acts) != 3:
                print('Fail: split_by_act, attempt 1', original_plan)
                acts = original_plan.split('Act ')
                if len(acts) == 4:
                    acts = acts[-3:]
                elif len(acts) != 3:
                    print('Fail: split_by_act, attempt 2', original_plan)
                    return []

        # 确保有3个幕
        if len(acts) != 3:
            print('Fail: split_by_act, final attempt failed, acts count:', len(acts))
            return []

        # 为每个幕添加标题前缀
        formatted_acts = []
        for i, act in enumerate(acts):
            if not act.strip().startswith('第'):
                formatted_acts.append(f'第{["一", "二", "三"][i]}幕: {act.strip()}')
            else:
                formatted_acts.append(act.strip())
        
        return formatted_acts

    @staticmethod
    def parse_act(act):
        # 处理中文格式的章节分割 - 修复正则表达式
        # 匹配 "第1章:", "第2章:" 等格式，不需要换行符开头
        chapters_split = re.split(r'第\d+章[:：]', act.strip())
        chapters = [text.strip() for text in chapters_split[1:]
                    if (text and (len(text.split()) > 3))]
        
        # 如果中文格式失败，尝试英文格式
        if not chapters:
            chapters_split = re.split(r'\n.{0,20}?Chapter .+:', act.strip())
            chapters = [text.strip() for text in chapters_split[1:]
                        if (text and (len(text.split()) > 3))]
        
        return {'act_descr': chapters_split[0].strip(), 'chapters': chapters}

    @staticmethod
    def parse_text_plan(text_plan):
        acts = Plan.split_by_act(text_plan)
        if not acts:
            return []
        plan = [Plan.parse_act(act) for act in acts if act]
        plan = [act for act in plan if act['chapters']]
        return plan

    @staticmethod
    def normalize_text_plan(text_plan):
        plan = Plan.parse_text_plan(text_plan)
        text_plan = Plan.plan_2_str(plan)
        return text_plan

    @staticmethod
    def act_2_str(plan, act_num):
        text_plan = ''
        chs = []
        ch_num = 1
        for i, act in enumerate(plan):
            act_descr = act['act_descr'] + '\n'
            if not re.search(r'Act \d', act_descr[0:50]):
                act_descr = f'Act {i+1}:\n' + act_descr
            for chapter in act['chapters']:
                if (i + 1) == act_num:
                    act_descr += f'- Chapter {ch_num}: {chapter}\n'
                    chs.append(ch_num)
                elif (i + 1) > act_num:
                    return text_plan.strip(), chs
                ch_num += 1
            text_plan += act_descr + '\n'
        return text_plan.strip(), chs

    @staticmethod
    def plan_2_str(plan):
        text_plan = ''
        ch_num = 1
        for i, act in enumerate(plan):
            act_descr = act['act_descr'] + '\n'
            if not re.search(r'Act \d', act_descr[0:50]):
                act_descr = f'Act {i+1}:\n' + act_descr
            for chapter in act['chapters']:
                act_descr += f'- Chapter {ch_num}: {chapter}\n'
                ch_num += 1
            text_plan += act_descr + '\n'
        return text_plan.strip()

    @staticmethod
    def save_plan(plan, fpath):
        with open(fpath, 'w') as fp:
            json.dump(plan, fp, indent=4)
