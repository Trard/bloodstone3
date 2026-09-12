#version 330

#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:projection.glsl>

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in ivec2 UV2;

uniform sampler2D Sampler2;

out float sphericalVertexDistance;
out float cylindricalVertexDistance;
out vec4 vertexColor;
out vec2 texCoord0;
out vec2 bseScreenPosition;
flat out int bseLetterbox;
flat out int bseScare;
flat out int bseCameraPhase;
flat out int bseCameraSeed;

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);
    sphericalVertexDistance = fog_spherical_distance(Position);
    cylindricalVertexDistance = fog_cylindrical_distance(Position);
    vertexColor = Color * texelFetch(Sampler2, UV2 / 16, 0);
    texCoord0 = UV0;
    bseScreenPosition = vec2(0.0);
    bseLetterbox = 0;
    bseScare = 0;
    bseCameraPhase = -1;
    bseCameraSeed = 0;

    // Only the dedicated bse:cutscene_letterbox title uses this marker.
    // Orthographic projection excludes world text / text displays entirely.
    bool marker = all(lessThan(abs(Color.rgb * 255.0 - vec3(253.0, 126.0, 1.0)), vec3(0.25)));
    if (marker && abs(ProjMat[3][3] - 1.0) < 0.001) {
        // Glyph vertices are TL, BL, BR, TR, regardless of font/GUI scale.
        const vec2 corners[4] = vec2[4](
            vec2(-1.0, 1.0), vec2(-1.0, -1.0),
            vec2(1.0, -1.0), vec2(1.0, 1.0)
        );
        bseScreenPosition = corners[gl_VertexID % 4];
        gl_Position = vec4(bseScreenPosition, 0.0, 1.0);
        bseLetterbox = 1;
    }
    // Dedicated scare fonts: a full-viewport background plus 4x4 portrait tiles.
    // The RGB marker encodes tile coordinates, not a tint. Other fonts stay vanilla.
    ivec3 tag = ivec3(round(Color.rgb * 255.0));
    bool cameraOff = tag.r == 251 && tag.g == 90 && tag.b >= 0 && tag.b < 3;
    bool cameraNoise = tag.r == 251 && tag.g == 91 && tag.b >= 0 && tag.b < 64;
    if (abs(ProjMat[3][3] - 1.0) < 0.001 && (cameraOff || cameraNoise)) {
        const vec2 cameraQuad[4] = vec2[4](vec2(-1,1),vec2(-1,-1),vec2(1,-1),vec2(1,1));
        bseScreenPosition = cameraQuad[gl_VertexID % 4];
        gl_Position = vec4(bseScreenPosition, 0.0, 1.0);
        bseCameraPhase = cameraOff ? tag.b : 3;
        bseCameraSeed = tag.b;
        vertexColor = vec4(1.0, 1.0, 1.0, Color.a);
    }
    bool background = tag == ivec3(252, 99, 99);
    bool portrait = tag.r == 252 && tag.g >= 100 && tag.g <= 103 && tag.b >= 100 && tag.b <= 103;
    if (abs(ProjMat[3][3] - 1.0) < 0.001 && (background || portrait)) {
        const vec2 quad[4] = vec2[4](vec2(0,0),vec2(0,1),vec2(1,1),vec2(1,0));
        vec2 uv = quad[gl_VertexID % 4];
        vec2 point = vec2(uv.x * 2.0 - 1.0, 1.0 - uv.y * 2.0);
        if (portrait) {
            uv = (vec2(tag.g - 100, tag.b - 100) + uv) / 4.0;
            point = vec2(uv.x * 2.0 - 1.0, 1.0 - uv.y * 2.0);
            float aspect = abs(ProjMat[1][1] / ProjMat[0][0]);
            // Fit a square portrait without stretching or cropping its face.
            point *= vec2(0.96 / max(1.0, aspect), 0.96 * min(1.0, aspect));
        }
        gl_Position = vec4(point, background ? 0.05 : 0.0, 1.0);
        bseScare = 1;
        vertexColor = vec4(1.0, 1.0, 1.0, Color.a);
    }
}
