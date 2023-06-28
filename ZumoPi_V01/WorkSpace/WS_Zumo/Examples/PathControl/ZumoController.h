#ifndef ZumoController_h
#define ZumoController_h

#include <Zumo32U4.h>
#include <Wire.h>

class ZumoController
{
public:
    struct CarState {
        float posx;
        float posy;
        float theta;
        float gyroAngle;
        bool motorState;
        float v_left;
        float v_right;
    };

    struct PathState {
        float v_forward;
        float theta_t;
        float de;
        float dist;
        int currPoint;
    };

    // public variabvles
    CarState car_state;
    PathState path_state;

    float a_max = 0.1;
    float v_max = 0.15;
    float Kp = 2000;
    float Ki = 25;
    float dt_time = 0.01;

    ZumoController();
    void begin();
    void reset();
    void control();
    void odometry();
    void gyroOffset();
    void gyroIntegration();
    void motorsSetSpeed(int leftSpeed, int rightSpeed);
    void P2P_CTRL(float desired_pos[][2], int numPoints);
    
private:

    const float GEAR_RATIO = 100;
    const float WHEELS_DISTANCE = 0.112; //WHEELS_DISTANCE = 0.098; //square: 0.101;
    const float WHEEL_DIAMETER = 0.0375;
    const float ENCODER_PPR = 12;
    const float encoder2dist = WHEEL_DIAMETER * 3.14 / (ENCODER_PPR * GEAR_RATIO);

    float err_sum_left = 0.0f;
    float err_sum_right = 0.0f;
    float v_l_target = 0.0f;
    float v_r_target = 0.0f;
    float prev_v_forward = 0.0f;
    int32_t gyroOffset_z = 0;
    float Kp_theta = 0.25f;
    float Kp_de = 0.75f;

    Zumo32U4Encoders encoders;
    Zumo32U4Motors motors;
    Zumo32U4IMU imu;
};

#endif
