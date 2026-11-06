#version 330
#extension GL_ARB_separate_shader_objects : require

uniform sampler2D InSampler;
layout(location = 0) in vec2 texCoord;
layout(std140) uniform EyelidConfig {
    float Closure;
};
layout(location = 0) out vec4 fragColor;

void main() {
    if (Closure >= 0.999) {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }
    vec2 position = texCoord * 2.0 - 1.0;
    float height = (1.0 - Closure) * (1.3 - 0.25 * position.x * position.x);
    float visible = 1.0 - smoothstep(height - 0.018, height + 0.018, abs(position.y));
    fragColor = vec4(texture(InSampler, texCoord).rgb * visible, 1.0);
}
