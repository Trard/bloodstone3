// Geometry and face UVs from unicorn_horse_horn.json (unicorn_horn.json with the handle removed).
const vec3 hornFrom[5] = vec3[5](
    vec3(6.5, 0.5, 7.0),
    vec3(7.0, 1.0, 3.0),
    vec3(6.0, 0.0, 12.0),
    vec3(5.5, -0.50195, 16.00564),
    vec3(5.3, -0.70195, 17.50564));
const vec3 hornTo[5] = vec3[5](
    vec3(9.5, 3.5, 13.0),
    vec3(9.0, 3.0, 8.0),
    vec3(10.0, 4.0, 16.0),
    vec3(10.5, 4.49805, 19.00564),
    vec3(10.7, 4.69805, 18.50564));
const vec4 hornUV[30] = vec4[30](
    vec4(3.0, 8.0, 6.0, 9.5), vec4(0.0, 8.0, 3.0, 9.5), vec4(9.0, 8.0, 7.5, 11.0), vec4(7.5, 11.0, 6.0, 8.0), vec4(11.0, 2.0, 12.5, 3.5), vec4(11.0, 8.0, 12.5, 9.5),
    vec4(11.0, 1.0, 13.5, 2.0), vec4(11.0, 0.0, 13.5, 1.0), vec4(8.0, 11.0, 7.0, 13.5), vec4(7.0, 13.5, 6.0, 11.0), vec4(9.0, 4.0, 10.0, 5.0), vec4(0.0, 11.5, 1.0, 12.5),
    vec4(0.0, 9.5, 2.0, 11.5), vec4(9.0, 2.0, 11.0, 4.0), vec4(6.0, 9.5, 4.0, 11.5), vec4(4.0, 11.5, 2.0, 9.5), vec4(9.0, 0.0, 11.0, 2.0), vec4(9.0, 8.0, 11.0, 10.0),
    vec4(9.0, 10.0, 10.5, 12.5), vec4(10.0, 4.0, 11.5, 6.5), vec4(13.0, 10.0, 10.5, 11.5), vec4(12.5, 8.0, 10.0, 6.5), vec4(0.0, 5.5, 2.5, 8.0), vec4(2.5, 5.5, 5.0, 8.0),
    vec4(8.5, 11.0, 9.0, 13.5), vec4(8.0, 11.0, 8.5, 13.5), vec4(13.5, 9.5, 11.0, 10.0), vec4(13.5, 4.0, 11.0, 3.5), vec4(5.0, 5.5, 7.5, 8.0), vec4(7.5, 5.5, 10.0, 8.0));

// Close the square end of the last segment with four triangular facets.
// Its base exactly matches the end face of the narrowest original cube.
vec3 hornPigment(vec3 albedo, float shade) {
    return albedo * (0.68 * shade);
}

bool hitHornPoint(vec3 origin, vec3 ray, float nearest, out vec3 color) {
    vec3 endCenter = 0.5 * (hornFrom[1] + hornTo[1]);
    endCenter.z = hornFrom[1].z;
    const float lengthToPoint = 2.6;
    vec3 apex = endCenter - vec3(0.0, 0.0, lengthToPoint);
    const vec2 sides[4] = vec2[4](vec2(1,0), vec2(-1,0), vec2(0,1), vec2(0,-1));
    for (int i = 0; i < 4; ++i) {
        vec3 normal = vec3(sides[i], -1.0 / lengthToPoint);
        float incidence = dot(normal, ray);
        if (incidence >= -1e-6) continue;
        float t = dot(normal, apex - origin) / incidence;
        if (t <= 0.0 || t >= nearest) continue;
        vec3 local = origin + t * ray - apex;
        float width = local.z / lengthToPoint;
        float across = dot(local.xy, sides[i].yx);
        if (width < 0.0 || width > 1.0 || abs(across) > width + 0.0001) continue;
        // Carry the two-pixel pink band and side shadow from the final segment onto the point.
        int row = (i == 0 || i == 2) ? 0 : 2;
        if (width > 0.52 + 0.28 * across) row += 1;
        color = hornPigment(texelFetch(Sampler0, ivec2(24, row + 2), 0).rgb, 0.94);
        return true;
    }
    return false;
}

// Recover the animated skull basis from its native UV plane, including renderer scale,
// rider turns and head pitch. All five solids use the original model's coordinate system.
vec4 hornSurface(vec2 uv) {
    vec2 p = uv * 64.0 - vec2(10.0, 16.0);
    vec4 bounds = vec4((3.0-p.x)/1.6, (3.0+p.x)/1.6, (3.85-p.y)/0.45, (2.5+p.y)/1.25);
    float roof = min(min(bounds.x, bounds.y), min(bounds.z, bounds.w));
    float height = hornFacet == 5 ? 1.0 : bounds[hornFacet-1];
    vec2 dx = dFdx(p), dy = dFdy(p);
    vec3 px = dFdx(hornPlane.xyz), py = dFdy(hornPlane.xyz);
    float det = dx.x*dy.y - dx.y*dy.x;
    if (hornPlane.w < 0.99999 || abs(det)<1e-12 || height < -0.01 || height > 1.01 || height > roof+0.005) discard;
    vec3 east = (px*dy.y - py*dx.y)/det;
    vec3 forward = (py*dx.x - px*dy.x)/det;
    vec3 base = hornPlane.xyz - east*p.x - forward*p.y;
    // The armor cube adds 0.1 pixels of deformation on each side of the six-pixel skull.
    float pixel = length(east)*(6.0/6.2)*0.55;
    vec3 xAxis = normalize(east), up = normalize(hornUp), front = normalize(forward);
    // The horn axis is perpendicular to the forehead. Seat its collar into the skin.
    base -= up * pixel * 1.75;
    mat3 basis = mat3(xAxis, front, -up);
    vec3 anchor = vec3(8.0, 1.99805, 19.00564);
    vec3 origin = anchor + transpose(basis)*(-base)/pixel;
    vec3 dir = transpose(basis)*normalize(hornView);
    vec3 inv = vec3(dir.x < 0.0 ? -1.0 : 1.0, dir.y < 0.0 ? -1.0 : 1.0, dir.z < 0.0 ? -1.0 : 1.0) / max(abs(dir),vec3(1e-7));
    float best = 1e20;
    int face = 0, which = -1;
    for (int i=0; i<5; ++i) {
        vec3 a=(hornFrom[i]-origin)*inv, b=(hornTo[i]-origin)*inv;
        vec3 low=min(a,b), high=max(a,b);
        float entry=max(low.x,max(low.y,low.z)), leave=min(high.x,min(high.y,high.z));
        if (entry < 0.0 || entry > leave || entry >= best) continue;
        best=entry;
        which=i;
        if (entry==low.x) face=dir.x>0.0?0:1;
        else if (entry==low.y) face=dir.y>0.0?2:3;
        else face=dir.z>0.0?4:5;
    }
    vec3 pointColor;
    if (hitHornPoint(origin, dir, best, pointColor)) return vec4(pointColor, 1.0);
    if (which<0) discard;
    vec3 q=clamp((origin+dir*best-hornFrom[which])/(hornTo[which]-hornFrom[which]),0.0,1.0);
    vec2 coords;
    if (face==0) coords=vec2(q.z,1.0-q.y);
    else if (face==1) coords=vec2(1.0-q.z,1.0-q.y);
    else if (face==2) coords=vec2(q.x,1.0-q.z);
    else if (face==3) coords=q.xz;
    else if (face==4) coords=vec2(1.0-q.x,1.0-q.y);
    else coords=vec2(q.x,1.0-q.y);
    vec4 rect=hornUV[which*6+face];
    vec2 texel=mix(rect.xy, rect.zw, clamp(coords,0.0001,0.9999))*2.0;
    vec4 albedo=texelFetch(Sampler0,ivec2(texel)+ivec2(2),0);
    if (albedo.a<0.001) discard;
    float shade = (face == 0 || face == 2) ? 0.92 : 1.0;
    return vec4(hornPigment(albedo.rgb, shade), 1.0);
}
