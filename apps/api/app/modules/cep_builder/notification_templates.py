"""
Notification Template System

Jinja2 기반 알림 메시지 템플릿 시스템
"""

import logging
from typing import Any, Dict, Optional

from jinja2 import Environment, Template, TemplateSyntaxError, UndefinedError

logger = logging.getLogger(__name__)


# 기본 템플릿들
DEFAULT_SLACK_TEMPLATE = """\
*{{ alert_title }}*

{{ alert_message }}
{% if severity %}🔴 *Severity*: {{ severity }}{% endif %}
{% if rule_name %}📋 *Rule*: {{ rule_name }}{% endif %}
{% if timestamp %}⏰ *Time*: {{ timestamp }}{% endif %}

{% if metadata %}*Additional Info:*
{% for key, value in metadata.items() %}
• *{{ key }}*: {{ value }}
{% endfor %}
{% endif %}\
"""

DEFAULT_EMAIL_TEMPLATE = """\
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 8px;">

        <h2 style="color: #e74c3c; margin-top: 0;">{{ alert_title }}</h2>

        <p style="font-size: 16px; line-height: 1.8;">{{ alert_message }}</p>

        <div style="background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0;">
            {% if severity %}
            <p style="margin: 8px 0;"><strong>Severity:</strong>
                {% if severity == 'critical' %}
                    <span style="color: #c0392b; font-weight: bold;">🔴 CRITICAL</span>
                {% elif severity == 'error' %}
                    <span style="color: #e74c3c;">🟠 ERROR</span>
                {% elif severity == 'warning' %}
                    <span style="color: #f39c12;">🟡 WARNING</span>
                {% else %}
                    <span style="color: #3498db;">🔵 {{ severity }}</span>
                {% endif %}
            </p>
            {% endif %}

            {% if rule_name %}
            <p style="margin: 8px 0;"><strong>Rule:</strong> {{ rule_name }}</p>
            {% endif %}

            {% if timestamp %}
            <p style="margin: 8px 0;"><strong>Time:</strong> {{ timestamp }}</p>
            {% endif %}
        </div>

        {% if metadata %}
        <div style="margin: 20px 0;">
            <h4 style="color: #2c3e50; margin-top: 0;">Additional Information</h4>
            <ul style="list-style: none; padding: 0; margin: 10px 0;">
                {% for key, value in metadata.items() %}
                <li style="padding: 8px 0; border-bottom: 1px solid #ecf0f1;">
                    <strong>{{ key }}:</strong> <code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px;">{{ value }}</code>
                </li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}

        <div style="border-top: 1px solid #bdc3c7; margin-top: 20px; padding-top: 15px; font-size: 12px; color: #7f8c8d;">
            <p style="margin: 5px 0;">This is an automated alert from Tobit CEP System.</p>
            <p style="margin: 5px 0;">Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>\
"""

DEFAULT_WEBHOOK_TEMPLATE = """\
{
  "alert": {
    "title": "{{ alert_title }}",
    "message": "{{ alert_message }}",
    "severity": "{{ severity }}",
    "rule_name": "{{ rule_name }}"
  },
  "metadata": {
    "timestamp": "{{ timestamp }}"{% if metadata %},
    {% for key, value in metadata.items() %}"{{ key }}": "{{ value }}"{% if not loop.last %},{% endif %}{% endfor %}{% endif %}
  }
}\
"""

DEFAULT_SMS_TEMPLATE = """\
[{{ severity|upper }}] {{ alert_title }}
{{ alert_message|truncate(140, true, '...') }}
Rule: {{ rule_name }}\
"""


class NotificationTemplate:
    """알림 템플릿"""

    def __init__(
        self,
        name: str,
        template_str: str,
        channel_type: str = "slack",
        is_default: bool = False,
    ):
        """
        초기화

        Args:
            name: 템플릿 이름
            template_str: Jinja2 템플릿 문자열
            channel_type: 채널 타입 (slack, email, webhook, sms)
            is_default: 기본 템플릿 여부
        """
        self.name = name
        self.channel_type = channel_type
        self.is_default = is_default

        try:
            self.template = Template(template_str)
            self.raw = template_str
        except TemplateSyntaxError as e:
            logger.error(f"Template syntax error in '{name}': {str(e)}")
            raise

    def render(self, context: Dict[str, Any]) -> str:
        """
        템플릿 렌더링

        Args:
            context: 템플릿 변수 딕셔너리

        Returns:
            렌더링된 메시지
        """
        try:
            return self.template.render(**context)
        except UndefinedError as e:
            logger.warning(f"Undefined variable in template '{self.name}': {str(e)}")
            # 정의되지 않은 변수를 빈 문자열로 처리
            env = Environment()
            template = env.from_string(self.raw)
            # 유효한 변수만 전달
            safe_context = {
                k: v for k, v in context.items() if not k.startswith("_")
            }
            return template.render(**safe_context)
        except Exception as e:
            logger.error(f"Error rendering template '{self.name}': {str(e)}")
            raise

    def validate(self, context: Dict[str, Any]) -> bool:
        """
        템플릿 검증

        Args:
            context: 테스트용 컨텍스트

        Returns:
            유효성 여부
        """
        try:
            self.render(context)
            return True
        except Exception:
            return False

    def get_variables(self) -> set:
        """
        템플릿에 필요한 변수 목록 조회

        Returns:
            필요한 변수명 set
        """
        # Jinja2 템플릿에서 변수 추출
        from jinja2 import meta

        env = Environment()
        ast = env.parse(self.raw)
        variables = meta.find_undeclared_variables(ast)
        return variables

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "name": self.name,
            "channel_type": self.channel_type,
            "is_default": self.is_default,
            "required_variables": list(self.get_variables()),
        }


class NotificationTemplateLibrary:
    """알림 템플릿 라이브러리"""

    def __init__(self):
        """초기화"""
        self.templates: Dict[str, NotificationTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self) -> None:
        """기본 템플릿 로드"""
        defaults = [
            NotificationTemplate(
                "slack_default",
                DEFAULT_SLACK_TEMPLATE,
                channel_type="slack",
                is_default=True,
            ),
            NotificationTemplate(
                "email_default",
                DEFAULT_EMAIL_TEMPLATE,
                channel_type="email",
                is_default=True,
            ),
            NotificationTemplate(
                "webhook_default",
                DEFAULT_WEBHOOK_TEMPLATE,
                channel_type="webhook",
                is_default=True,
            ),
            NotificationTemplate(
                "sms_default",
                DEFAULT_SMS_TEMPLATE,
                channel_type="sms",
                is_default=True,
            ),
        ]

        for template in defaults:
            self.templates[template.name] = template

    def add_template(self, template: NotificationTemplate) -> None:
        """
        템플릿 추가

        Args:
            template: 추가할 템플릿
        """
        self.templates[template.name] = template
        logger.info(f"Template added: {template.name}")

    def get_template(self, name: str) -> Optional[NotificationTemplate]:
        """
        템플릿 조회

        Args:
            name: 템플릿 이름

        Returns:
            템플릿 (없으면 None)
        """
        return self.templates.get(name)

    def get_default_template(self, channel_type: str) -> Optional[NotificationTemplate]:
        """
        채널별 기본 템플릿 조회

        Args:
            channel_type: 채널 타입

        Returns:
            기본 템플릿 (없으면 None)
        """
        for template in self.templates.values():
            if template.channel_type == channel_type and template.is_default:
                return template
        return None

    def list_templates(self, channel_type: Optional[str] = None) -> Dict[str, Any]:
        """
        템플릿 목록 조회

        Args:
            channel_type: 채널 타입 필터 (선택)

        Returns:
            템플릿 목록
        """
        result = {}
        for name, template in self.templates.items():
            if channel_type and template.channel_type != channel_type:
                continue
            result[name] = template.to_dict()
        return result

    def remove_template(self, name: str) -> bool:
        """
        템플릿 삭제

        Args:
            name: 템플릿 이름

        Returns:
            삭제 성공 여부
        """
        template = self.get_template(name)
        if not template or template.is_default:
            logger.warning(
                f"Cannot remove template '{name}' (default or not found)"
            )
            return False

        del self.templates[name]
        logger.info(f"Template removed: {name}")
        return True


# 전역 템플릿 라이브러리
template_library = NotificationTemplateLibrary()


def render_notification_message(
    message_title: str,
    message_body: str,
    template_name: Optional[str] = None,
    channel_type: str = "slack",
    **context,
) -> str:
    """
    알림 메시지 렌더링

    Args:
        message_title: 알림 제목
        message_body: 알림 본문
        template_name: 템플릿 이름 (미지정 시 기본 템플릿)
        channel_type: 채널 타입
        **context: 템플릿 변수

    Returns:
        렌더링된 메시지
    """
    # 템플릿 선택
    if template_name:
        template = template_library.get_template(template_name)
        if not template:
            logger.warning(f"Template '{template_name}' not found, using default")
            template = template_library.get_default_template(channel_type)
    else:
        template = template_library.get_default_template(channel_type)

    if not template:
        logger.error(f"No template found for channel type '{channel_type}'")
        return message_body

    # 컨텍스트 준비
    render_context = {
        "alert_title": message_title,
        "alert_message": message_body,
        **context,
    }

    # 렌더링
    return template.render(render_context)
